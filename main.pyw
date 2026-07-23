import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import random
import traceback
import re
import asyncio
from datetime import datetime
from gtts import gTTS
from io import BytesIO
import pyttsx3
import edge_tts  # ★新エンジン追加！

class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("究極版・自動調整 音声読み上げツール (Edge-TTS/超高音質・長文対応)")
        self.root.geometry("750x950")
        self.root.configure(padx=20, pady=20)

        self.auto_adjust_enabled = True
        self._after_id = None  # テキスト変更検知のタイマー
        self.file_text = None  # 読み込んだファイルの内容を保持する変数
        
        self.create_widgets()

    def create_widgets(self):
        # --- 1. エンジン選択エリア ---
        engine_frame = tk.LabelFrame(self.root, text="1. 音声合成エンジンの選択", padx=10, pady=5)
        engine_frame.pack(fill="x", pady=(0, 10))

        self.engine_var = tk.StringVar(value="edge-tts")

        tk.Radiobutton(engine_frame, text="Edge-TTS (★推奨 / 超高音質・制限ほぼなし・男女選択可)", 
                       variable=self.engine_var, value="edge-tts", font=("Arial", 10, "bold"), fg="blue",
                       command=self.toggle_params_state).pack(anchor="w", pady=2)

        tk.Radiobutton(engine_frame, text="gTTS (Google翻訳の裏技 / 制限厳しめ・長文非推奨)", 
                       variable=self.engine_var, value="gTTS", font=("Arial", 10),
                       command=self.toggle_params_state).pack(anchor="w", pady=2)
                       
        tk.Radiobutton(engine_frame, text="pyttsx3 (PC内蔵の旧音声 / 通信不要・一括処理のみ)", 
                       variable=self.engine_var, value="pyttsx3", font=("Arial", 10),
                       command=self.toggle_params_state).pack(anchor="w", pady=2)

        # --- 2. 言語と声質（性別）選択エリア ---
        lang_frame = tk.LabelFrame(self.root, text="2. 言語と声質(性別)の選択", padx=10, pady=5)
        lang_frame.pack(fill="x", pady=(0, 10))

        self.lang_var = tk.StringVar(value="ja")
        self.gender_var = tk.StringVar(value="Male")

        tk.Label(lang_frame, text="【言語】", font=("Arial", 9, "bold")).grid(row=0, column=0, pady=5, sticky="e")
        tk.Radiobutton(lang_frame, text="日本語", variable=self.lang_var, value="ja", font=("Arial", 10)).grid(row=0, column=1, padx=10)
        tk.Radiobutton(lang_frame, text="英語", variable=self.lang_var, value="en", font=("Arial", 10)).grid(row=0, column=2, padx=10)

        tk.Label(lang_frame, text="【声質 (Edge専用)】", font=("Arial", 9, "bold")).grid(row=1, column=0, pady=5, sticky="e")
        tk.Radiobutton(lang_frame, text="男性 (Keita / Guy)", variable=self.gender_var, value="Male", font=("Arial", 10)).grid(row=1, column=1, padx=10)
        tk.Radiobutton(lang_frame, text="女性 (Nanami / Aria)", variable=self.gender_var, value="Female", font=("Arial", 10)).grid(row=1, column=2, padx=10)

        # --- 3. テキスト入力エリア (ファイル読み込み機能) ---
        input_header_frame = tk.Frame(self.root)
        input_header_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(input_header_frame, text="3. 読み上げたいテキスト (直接入力 or ファイル選択):", font=("Arial", 10, "bold")).pack(side="left")
        
        # ファイル選択ボタン
        self.load_btn = tk.Button(input_header_frame, text="📁 テキストファイル(.txt)を選択", font=("Arial", 9, "bold"), bg="#f0f0f0", command=self.load_from_file)
        self.load_btn.pack(side="right", padx=5)

        # ファイル選択解除ボタン
        self.clear_file_btn = tk.Button(input_header_frame, text="✖ 選択解除", font=("Arial", 9), fg="red", command=self.clear_file_selection, state="disabled")
        self.clear_file_btn.pack(side="right", padx=5)
        
        text_frame = tk.Frame(self.root)
        text_frame.pack(fill="both", expand=True, pady=(5, 10))
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.text_area = tk.Text(text_frame, height=8, font=("Arial", 11), yscrollcommand=scrollbar.set)
        self.text_area.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_area.yview)

        self.text_area.bind("<<Modified>>", self.on_text_modified)

        self.char_count_label = tk.Label(self.root, text="現在の文字数: 0文字", fg="blue", font=("Arial", 10, "bold"))
        self.char_count_label.pack(anchor="e")

        # --- 4. パラメータ設定エリア ---
        self.param_frame = tk.LabelFrame(self.root, text="4. 変換パラメータ（自動調整 / 手動変更可）", padx=10, pady=10)
        self.param_frame.pack(fill="x", pady=10)

        tk.Label(self.param_frame, text="1回の処理文字数 (チャンク):").grid(row=0, column=0, sticky="e", pady=5)
        self.chunk_var = tk.StringVar(value="1000")
        self.chunk_entry = tk.Entry(self.param_frame, textvariable=self.chunk_var, width=10)
        self.chunk_entry.grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(self.param_frame, text="待機時間 (最小) 秒:").grid(row=0, column=2, sticky="e", pady=5)
        self.wait_min_var = tk.StringVar(value="1.0")
        self.wait_min_entry = tk.Entry(self.param_frame, textvariable=self.wait_min_var, width=10)
        self.wait_min_entry.grid(row=0, column=3, sticky="w", padx=5)

        tk.Label(self.param_frame, text="待機時間 (最大) 秒:").grid(row=1, column=2, sticky="e", pady=5)
        self.wait_max_var = tk.StringVar(value="2.0")
        self.wait_max_entry = tk.Entry(self.param_frame, textvariable=self.wait_max_var, width=10)
        self.wait_max_entry.grid(row=1, column=3, sticky="w", padx=5)

        for entry in (self.chunk_entry, self.wait_min_entry, self.wait_max_entry):
            entry.bind("<KeyRelease>", self.disable_auto_adjust)

        self.reset_btn = tk.Button(self.param_frame, text="自動調整に戻す", command=self.enable_auto_adjust, state="disabled")
        self.reset_btn.grid(row=1, column=0, columnspan=2, pady=5)

        # --- プログレスバーとステータス ---
        self.status_label = tk.Label(self.root, text="待機中...", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=(5, 5))

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=100, mode="determinate")
        self.progress.pack(fill="x", pady=5)

        # --- 実行ボタン ---
        self.start_btn = tk.Button(self.root, text="音声を生成して保存", font=("Arial", 12, "bold"), bg="#4CAF50", fg="black", command=self.start_processing)
        self.start_btn.pack(pady=10, ipady=10, ipadx=20)

        # --- 5. エラー表示エリア ---
        self.error_frame = tk.LabelFrame(self.root, text="5. エラーログ (問題発生時のみ出力されます)", fg="red", padx=10, pady=5)
        self.error_frame.pack(fill="both", expand=True, pady=(0, 10))

        error_scroll = tk.Scrollbar(self.error_frame)
        error_scroll.pack(side="right", fill="y")

        self.error_area = tk.Text(self.error_frame, height=4, font=("Consolas", 9), fg="red", yscrollcommand=error_scroll.set)
        self.error_area.pack(side="left", fill="both", expand=True)
        error_scroll.config(command=self.error_area.yview)
        
        self.error_area.insert(tk.END, "※エラーは発生していません。")
        self.error_area.config(state="disabled")

    # --- ロジック: テキストファイル読み込み (超高速化版) ---
    def load_from_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="読み込むテキストファイルを選択してください"
        )
        if not filepath:
            return

        try:
            # ファイルの読み込み自体は一瞬で終わる
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="cp932") as f:
                    content = f.read()

            self.file_text = content

            # テキストエリアにはプレビューを描画せず、メッセージだけ表示してロックする
            self.text_area.config(state="normal")
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, f"【ファイル選択中】\n{filepath}\n\n※ファイルから直接読み込んで変換します。\n※動作を軽くするため、テキストのプレビューは省略されています。")
            self.text_area.config(state="disabled")

            self.clear_file_btn.config(state="normal")

            # 文字数・パラメータの即時更新
            text_length = len(self.file_text)
            self.char_count_label.config(text=f"現在の文字数: {text_length:,} 文字 (ファイル)")
            
            if self.auto_adjust_enabled and text_length > 0:
                self.calculate_and_set_parameters(text_length)
            
            self.status_label.config(text="ファイルを選択しました。保存ボタンを押して変換を開始してください。", fg="blue")

        except Exception as e:
            self._show_error_in_app("ファイル読み込みエラー", str(e))

    def clear_file_selection(self):
        self.file_text = None
        
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", tk.END)
        
        self.clear_file_btn.config(state="disabled")
        self.status_label.config(text="待機中...", fg="black")
        
        self._update_text_info()

    # --- ロジック: エンジン切り替え時のUI制御 ---
    def toggle_params_state(self):
        engine = self.engine_var.get()
        state = "disabled" if engine == "pyttsx3" else "normal"
        
        self.chunk_entry.config(state=state)
        self.wait_min_entry.config(state=state)
        self.wait_max_entry.config(state=state)
        
        if engine == "pyttsx3":
            self.reset_btn.config(state="disabled")
        elif not self.auto_adjust_enabled:
            self.reset_btn.config(state="normal")

    # --- ロジック: テキスト変更検知と自動計算 ---
    def on_text_modified(self, event):
        if self.file_text is not None:
            self.text_area.edit_modified(False)
            return

        if self.text_area.edit_modified():
            if self._after_id is not None:
                self.root.after_cancel(self._after_id)
            
            self._after_id = self.root.after(500, self._update_text_info)
            self.text_area.edit_modified(False)

    def _update_text_info(self):
        if self.file_text is not None:
            text_length = len(self.file_text)
        else:
            text_length = len(self.text_area.get("1.0", "end-1c").strip())
            
        self.char_count_label.config(text=f"現在の文字数: {text_length:,} 文字")
        
        if self.auto_adjust_enabled and text_length > 0:
            self.calculate_and_set_parameters(text_length)

    def calculate_and_set_parameters(self, length):
        chunk_val = self.chunk_var.get()
        chunk = int(chunk_val) if chunk_val.isdigit() else 1000

        engine = self.engine_var.get()
        
        if engine == "gTTS":
            w_min, w_max = 3.0, 5.0
            if length >= 20000:
                extra_steps = (length - 10000) // 10000
                w_min += extra_steps * 0.5
                w_max += extra_steps * 0.5
        else:
            w_min, w_max = 1.0, 2.0
            if length >= 50000:
                w_min, w_max = 1.5, 3.0

        self.chunk_var.set(str(chunk))
        self.wait_min_var.set(f"{w_min:.1f}")
        self.wait_max_var.set(f"{w_max:.1f}")

    def disable_auto_adjust(self, event):
        if self.auto_adjust_enabled and self.engine_var.get() != "pyttsx3":
            self.auto_adjust_enabled = False
            self.reset_btn.config(state="normal")
            self.char_count_label.config(fg="red", text=self.char_count_label.cget("text").replace(" (手動設定中)", "") + " (手動設定中)")

    def enable_auto_adjust(self):
        self.auto_adjust_enabled = True
        self.reset_btn.config(state="disabled")
        self._update_text_info()

    # --- ロジック: スマートチャンク分割ヘルパー関数 ---
    def _create_smart_chunks(self, text, chunk_size):
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

    # --- ロジック: 実行処理の開始 ---
    def start_processing(self):
        # ファイルが選択されていればそれを優先、なければテキストエリアから取得
        if self.file_text is not None:
            text = self.file_text.strip()
        else:
            text = self.text_area.get("1.0", "end-1c").strip()
            
        if not text:
            messagebox.showwarning("警告", "テキストを入力するか、ファイルを選択してください。")
            return

        engine_choice = self.engine_var.get()
        lang_choice = self.lang_var.get()
        gender_choice = self.gender_var.get()
        chunk_size = w_min = w_max = 0

        if engine_choice in ["gTTS", "edge-tts"]:
            try:
                chunk_size = int(self.chunk_var.get())
                w_min = float(self.wait_min_var.get())
                w_max = float(self.wait_max_var.get())
            except ValueError:
                self._show_error_in_app("パラメータエラー", "待機時間やチャンク数には数値を入力してください。")
                return

        # 保存先ダイアログ
        default_ext = ".mp3" if engine_choice in ["gTTS", "edge-tts"] else ".wav"
        current_time_str = datetime.now().strftime("%Y%m%d_%H%M_audio") + default_ext
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            initialfile=current_time_str,
            filetypes=[("Audio Files", "*.mp3 *.wav"), ("All Files", "*.*")],
            title="保存先を選んでください"
        )
        if not save_path:
            return

        # UI無効化・初期化
        self.start_btn.config(state="disabled")
        self.load_btn.config(state="disabled")
        self.clear_file_btn.config(state="disabled")
        self.text_area.config(state="disabled")
        self.progress["value"] = 0
        self.status_label.config(fg="black", text="処理を開始します...")
        
        self.error_area.config(state="normal")
        self.error_area.delete("1.0", tk.END)
        self.error_area.config(state="disabled")

        # スレッド起動
        if engine_choice == "edge-tts":
            thread = threading.Thread(target=self.process_edge_tts_thread, args=(text, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path))
        elif engine_choice == "gTTS":
            thread = threading.Thread(target=self.process_gtts_thread, args=(text, chunk_size, w_min, w_max, lang_choice, save_path))
        else:
            thread = threading.Thread(target=self.process_pyttsx3_thread, args=(text, lang_choice, save_path))
            
        thread.daemon = True
        thread.start()

    # ==========================================================
    # 🌟 新エンジン: Edge-TTS処理スレッド
    # ==========================================================
    def process_edge_tts_thread(self, text, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path):
        try:
            asyncio.run(self._async_edge_tts_process(text, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path))
        except Exception as e:
            error_details = traceback.format_exc()
            self.root.after(0, self.finish_processing, False, str(e), error_details)

    async def _async_edge_tts_process(self, text, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path):
        voice = "ja-JP-NanamiNeural" 
        if lang_choice == "ja":
            voice = "ja-JP-KeitaNeural" if gender_choice == "Male" else "ja-JP-NanamiNeural"
        elif lang_choice == "en":
            voice = "en-US-GuyNeural" if gender_choice == "Male" else "en-US-AriaNeural"

        chunks = self._create_smart_chunks(text, chunk_size)
        total_chunks = len(chunks)
        combined_audio = bytearray()

        for i, chunk in enumerate(chunks):
            self.root.after(0, self.update_status, f"Edge-TTS処理中... {i+1} / {total_chunks} チャンク (男/女: {gender_choice})", (i / total_chunks) * 100)
            
            communicate = edge_tts.Communicate(chunk, voice)
            async for chunk_data in communicate.stream():
                if chunk_data["type"] == "audio":
                    combined_audio.extend(chunk_data["data"])
            
            if i < total_chunks - 1:
                sleep_time = random.uniform(w_min, w_max)
                self.root.after(0, self.update_status, f"サーバー負荷軽減のため待機中... ({sleep_time:.1f}秒)", (i / total_chunks) * 100)
                await asyncio.sleep(sleep_time)

        self.root.after(0, self.update_status, "ファイル保存中...", 99)
        with open(save_path, "wb") as f:
            f.write(combined_audio)

        self.root.after(0, self.finish_processing, True, f"保存完了: {save_path}", None)

    # ==========================================================
    # 旧エンジン: gTTS処理スレッド
    # ==========================================================
    def process_gtts_thread(self, text, chunk_size, w_min, w_max, lang_choice, save_path):
        try:
            chunks = self._create_smart_chunks(text, chunk_size)
            total_chunks = len(chunks)
            combined_audio = BytesIO()

            for i, chunk in enumerate(chunks):
                self.root.after(0, self.update_status, f"gTTS処理中... {i+1} / {total_chunks} チャンク", (i / total_chunks) * 100)
                
                tts = gTTS(text=chunk, lang=lang_choice)
                fp = BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                combined_audio.write(fp.read())
                
                if i < total_chunks - 1:
                    sleep_time = random.uniform(w_min, w_max)
                    self.root.after(0, self.update_status, f"制限回避のため待機中... ({sleep_time:.1f}秒)", (i / total_chunks) * 100)
                    time.sleep(sleep_time)

            self.root.after(0, self.update_status, "ファイル保存中...", 99)
            with open(save_path, "wb") as f:
                f.write(combined_audio.getvalue())

            self.root.after(0, self.finish_processing, True, f"保存完了: {save_path}", None)

        except Exception as e:
            error_details = traceback.format_exc()
            self.root.after(0, self.finish_processing, False, str(e), error_details)

    # ==========================================================
    # 旧エンジン: pyttsx3処理スレッド
    # ==========================================================
    def process_pyttsx3_thread(self, text, lang_choice, save_path):
        try:
            self.root.after(0, self.update_status, "pyttsx3で一括処理中... (※進捗バーは動きません)", 50)
            
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            for voice in voices:
                name_lower = voice.name.lower()
                if lang_choice == "ja" and ("japanese" in name_lower or "haruka" in name_lower):
                    engine.setProperty('voice', voice.id)
                    break
                elif lang_choice == "en" and ("english" in name_lower or "zira" in name_lower or "david" in name_lower):
                    engine.setProperty('voice', voice.id)
                    break

            engine.save_to_file(text, save_path)
            engine.runAndWait()

            self.root.after(0, self.finish_processing, True, f"保存完了: {save_path}", None)

        except Exception as e:
            error_details = traceback.format_exc()
            self.root.after(0, self.finish_processing, False, str(e), error_details)

    # --- 共通: UI更新・エラー表示系 ---
    def update_status(self, text, progress_val):
        self.status_label.config(text=text, fg="black")
        self.progress["value"] = progress_val

    def _show_error_in_app(self, summary, details=""):
        current_status = self.status_label.cget("text")
        self.status_label.config(text=f"処理停止 (エラー発生): {current_status}", fg="red")
        
        self.error_area.config(state="normal")
        self.error_area.delete("1.0", tk.END)
        self.error_area.insert(tk.END, f"【概要】\n{summary}\n\n【詳細なエラー情報】\n{details}")
        self.error_area.config(state="disabled")

    def finish_processing(self, success, message, error_details):
        self.start_btn.config(state="normal")
        self.load_btn.config(state="normal")
        
        if self.file_text is None:
            self.text_area.config(state="normal")
        else:
            self.clear_file_btn.config(state="normal")
        
        if success:
            self.status_label.config(text="完了", fg="blue")
            self.progress["value"] = 100
            
            self.error_area.config(state="normal")
            self.error_area.delete("1.0", tk.END)
            self.error_area.insert(tk.END, "※エラーは発生していません。")
            self.error_area.config(state="disabled")
            
            messagebox.showinfo("完了", message)
        else:
            self._show_error_in_app(message, error_details)

if __name__ == "__main__":
    root = tk.Tk()
    app = TTSApp(root)
    root.mainloop()