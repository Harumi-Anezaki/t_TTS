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

    def process(self, text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str) -> None:
        """To be implemented by subclasses."""
        raise NotImplementedError()


class EdgeTTSEngine(TTSEngineBase):
    """Handles Microsoft Edge TTS generation asynchronously."""
    
    def process(self, text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str) -> None:
        self.update_status("[3/5] Windows非同期環境を設定中...", 5)
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self.update_status("[4/5] Edge-TTSエンジンを初期化中...", 10)
        asyncio.run(self._async_process(text, chunk_size, w_min, w_max, lang, gender, save_path))

    async def _async_process(self, text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str) -> None:
        self.update_status("[4/5] テキストを解析・分割中...", 15)
        voice = "ja-JP-NanamiNeural" 
        if lang == "ja":
            voice = "ja-JP-KeitaNeural" if gender == "Male" else "ja-JP-NanamiNeural"
        elif lang == "en":
            voice = "en-US-GuyNeural" if gender == "Male" else "en-US-AriaNeural"

        chunks = self._create_smart_chunks(text, chunk_size)
        total_chunks = len(chunks)
        combined_audio = bytearray()

        for i, chunk in enumerate(chunks):
            self.update_status(f"[5/5] Edge-TTS サーバーと通信中... ({i+1}/{total_chunks} チャンク)", (i / total_chunks) * 100)
            
            try:
                communicate = edge_tts.Communicate(chunk, voice)
                async for chunk_data in communicate.stream():
                    if chunk_data["type"] == "audio":
                        combined_audio.extend(chunk_data["data"])
            except Exception as e:
                raise Exception(f"Edge-TTSの通信中にエラーが発生しました。\nネットワーク接続がブロックされている可能性があります。\n詳細: {str(e)}")
            
            if i < total_chunks - 1:
                sleep_time = random.uniform(w_min, w_max)
                self.update_status(f"[5/5] アクセス制限回避のため待機中... ({sleep_time:.1f}秒)", (i / total_chunks) * 100)
                await asyncio.sleep(sleep_time)

        self.update_status("ファイルの書き込み中...", 99)
        with open(save_path, "wb") as f:
            f.write(combined_audio)


class GTTSEngine(TTSEngineBase):
    """Handles Google TTS generation."""
    
    def process(self, text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str) -> None:
        chunks = self._create_smart_chunks(text, chunk_size)
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
    
    def process(self, text: str, chunk_size: int, w_min: float, w_max: float, lang: str, gender: str, save_path: str) -> None:
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

        engine.save_to_file(text, save_path)
        engine.runAndWait()
