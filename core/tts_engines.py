import asyncio
import random
import re
import time
import traceback
from io import BytesIO
from typing import Callable, List

from gtts import gTTS
import pyttsx3
import edge_tts

class TTSEngineBase:
    """Base class for all TTS engines."""
    
    def __init__(self, update_status_cb: Callable[[str, float], None]):
        """
        Args:
            update_status_cb: Callback function to update UI status.
                              Signature: def callback(message: str, progress: float) -> None
        """
        self.update_status = update_status_cb

    def _create_smart_chunks(self, text: str, chunk_size: int) -> List[str]:
        """Splits text into chunks intelligently without breaking sentences."""
        parts = re.split(r'([。．.\n]+)', text)
        sentences = []
        for i in range(0, len(parts)-1, 2):
            sentences.append(parts[i] + parts[i+1])
        if len(parts) % 2 != 0 and parts[-1]:
            sentences.append(parts[-1])

        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                # Hard split if a single sentence is larger than chunk_size
                for j in range(0, len(sentence), chunk_size):
                    chunks.append(sentence[j:j+chunk_size])
                continue

            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def process(self, original_text: str, sanitized_text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str, output_format: str = "MP3", speed: float = 1.0) -> None:
        """To be implemented by subclasses."""
        raise NotImplementedError()


class EdgeTTSEngine(TTSEngineBase):
    """Handles Microsoft Edge TTS generation asynchronously."""
    
    def process(self, original_text: str, sanitized_text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str, output_format: str = "MP3", speed: float = 1.0) -> None:
        self.update_status("[3/5] Windows非同期環境を設定中...", 5)
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self.update_status("[4/5] Edge-TTSエンジンを初期化中...", 10)
        asyncio.run(self._async_process(original_text, sanitized_text, chunk_size, w_min, w_max, lang, gender, save_path, output_format, speed))

    async def _async_process(self, original_text: str, sanitized_text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str, output_format: str, speed: float) -> None:
        self.update_status("[4/5] テキストを解析・分割中...", 15)
        voice = "ja-JP-NanamiNeural" 
        if lang == "ja":
            voice = "ja-JP-KeitaNeural" if gender == "Male" else "ja-JP-NanamiNeural"
        else:
            voice = "en-US-GuyNeural" if gender == "Male" else "en-US-AriaNeural"
            
        chunks = self._create_smart_chunks(sanitized_text, chunk_size)
        total_chunks = len(chunks)
        combined_audio = bytearray()
        
        word_boundaries = []
        current_offset_compensation = 0

        for i, chunk in enumerate(chunks):
            self.update_status(f"[5/5] Edge-TTS サーバーと通信中... ({i+1}/{total_chunks} チャンク)", (i / total_chunks) * 100)
            
            chunk_audio = bytearray()
            chunk_word_boundaries = []
            
            try:
                communicate = edge_tts.Communicate(chunk, voice, boundary="WordBoundary")
                async for chunk_data in communicate.stream():
                    if chunk_data["type"] == "audio":
                        chunk_audio.extend(chunk_data["data"])
                    elif chunk_data["type"] == "WordBoundary":
                        chunk_word_boundaries.append({
                            "offset": chunk_data["offset"],
                            "duration": chunk_data["duration"],
                            "text": chunk_data["text"]
                        })
            except Exception as e:
                raise Exception(f"Edge-TTSの通信中にエラーが発生しました。\nネットワーク接続がブロックされている可能性があります。\n詳細: {str(e)}")
            
            chunk_dur = (len(chunk_audio) * 8 * 10_000_000) // 48000
            
            if chunk_word_boundaries:
                max_word_end = chunk_word_boundaries[-1]["offset"] + chunk_word_boundaries[-1]["duration"]
                target_max = max(0, chunk_dur - 100_000) # Leave 0.01s margin
                
                # If timestamps drift past the actual audio length, scale them down to fit
                if max_word_end > target_max and max_word_end > 0:
                    scale = target_max / max_word_end
                    for wb in chunk_word_boundaries:
                        wb["offset"] = int(wb["offset"] * scale)
                        wb["duration"] = int(wb["duration"] * scale)
                
                for wb in chunk_word_boundaries:
                    wb["offset"] += current_offset_compensation
                    word_boundaries.append(wb)
                    
            current_offset_compensation += chunk_dur
            combined_audio.extend(chunk_audio)
            
            if i < total_chunks - 1:
                sleep_time = random.uniform(w_min, w_max)
                self.update_status(f"[5/5] アクセス制限回避のため待機中... ({sleep_time:.1f}秒)", (i / total_chunks) * 100)
                await asyncio.sleep(sleep_time)

        self.update_status("ファイルの書き込み中...", 99)
        if output_format == "MP3":
            if speed != 1.0:
                import subprocess, os
                import imageio_ffmpeg
                temp_mp3 = save_path + ".tmp_speed.mp3"
                with open(temp_mp3, "wb") as f:
                    f.write(combined_audio)
                try:
                    self.update_status(f"音声を倍速化中 ({speed}x)...", 99)
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    cmd = [ffmpeg_exe, "-y", "-i", temp_mp3, "-filter:a", f"atempo={speed}", save_path]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
                finally:
                    if os.path.exists(temp_mp3):
                        os.remove(temp_mp3)
            else:
                with open(save_path, "wb") as f:
                    f.write(combined_audio)
        elif output_format == "HTML":
            import os
            from core.html_generator import HtmlGenerator
            
            temp_mp3 = save_path + ".tmp.mp3"
            with open(temp_mp3, "wb") as f:
                f.write(combined_audio)
                
            try:
                self.update_status("HTMLファイルを生成中...", 99)
                hg = HtmlGenerator(original_text, word_boundaries, temp_mp3, save_path, speed)
                hg.generate()
            finally:
                if os.path.exists(temp_mp3):
                    os.remove(temp_mp3)


class GTTSEngine(TTSEngineBase):
    """Handles Google TTS generation."""
    
    def process(self, original_text: str, sanitized_text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str, output_format: str = "MP3", speed: float = 1.0) -> None:
        chunks = self._create_smart_chunks(sanitized_text, chunk_size)
        total_chunks = len(chunks)
        combined_audio = BytesIO()

        for i, chunk in enumerate(chunks):
            self.update_status(f"gTTS処理中... {i+1} / {total_chunks} チャンク", (i / total_chunks) * 100)
            
            tts = gTTS(text=chunk, lang=lang)
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            combined_audio.write(fp.read())
            
            if i < total_chunks - 1:
                sleep_time = random.uniform(w_min, w_max)
                self.update_status(f"制限回避のため待機中... ({sleep_time:.1f}秒)", (i / total_chunks) * 100)
                time.sleep(sleep_time)

        self.update_status("ファイル保存中...", 99)
        with open(save_path, "wb") as f:
            f.write(combined_audio.getvalue())


class Pyttsx3Engine(TTSEngineBase):
    """Handles offline TTS generation using pyttsx3."""
    
    def process(self, original_text: str, sanitized_text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str, output_format: str = "MP3", speed: float = 1.0) -> None:
        self.update_status("pyttsx3で一括処理中... (※進捗バーは動きません)", 50)
        
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        for voice in voices:
            name_lower = voice.name.lower()
            if lang == "ja" and ("japanese" in name_lower or "haruka" in name_lower):
                engine.setProperty('voice', voice.id)
                break
            elif lang == "en" and ("english" in name_lower or "zira" in name_lower or "david" in name_lower):
                engine.setProperty('voice', voice.id)
                break
                
        if speed != 1.0:
            rate = engine.getProperty('rate')
            engine.setProperty('rate', int(rate * speed))
            
        engine.save_to_file(sanitized_text, save_path)
        engine.runAndWait()
