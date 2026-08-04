import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox
import threading
import traceback
from datetime import datetime

from core.logger import UILogger
from core.sanitizer import TextSanitizer
from core.tts_engines import EdgeTTSEngine, GTTSEngine, Pyttsx3Engine

class TTSUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        
        self.auto_adjust_enabled = True
        self._after_id = None
        self.file_text = None
        
        self.create_widgets()
        
        self.logger = UILogger(self.error_area, self.root)
        self.sanitizer = TextSanitizer(self.logger)
        self.sanitizer.load_rules()

    def create_widgets(self):
        # 1. Engine Selection
        engine_frame = ttk.Labelframe(self.root, text="1. 音声合成エンジンの選択", padding=10)
        engine_frame.pack(fill="x", pady=(0, 10))

        self.engine_var = ttk.StringVar(value="edge-tts")

        ttk.Radiobutton(engine_frame, text="Edge-TTS (★推奨 / 超高音質・制限ほぼなし・男女選択可)", 
                       variable=self.engine_var, value="edge-tts", bootstyle="info",
                       command=self.toggle_params_state).pack(anchor="w", pady=4)
        ttk.Radiobutton(engine_frame, text="gTTS (Google翻訳の裏技 / 制限厳しめ・長文非推奨)", 
                       variable=self.engine_var, value="gTTS",
                       command=self.toggle_params_state).pack(anchor="w", pady=4)
        ttk.Radiobutton(engine_frame, text="pyttsx3 (PC内蔵の旧音声 / 通信不要・一括処理のみ)", 
                       variable=self.engine_var, value="pyttsx3",
                       command=self.toggle_params_state).pack(anchor="w", pady=4)

        # 2. Language and Gender
        lang_frame = ttk.Labelframe(self.root, text="2. 言語と声質(性別)の選択", padding=10)
        lang_frame.pack(fill="x", pady=(0, 10))

        self.lang_var = ttk.StringVar(value="ja")
        self.gender_var = ttk.StringVar(value="Male")

        ttk.Label(lang_frame, text="【言語】", font=("Helvetica", 10, "bold")).grid(row=0, column=0, pady=5, sticky="e")
        ttk.Radiobutton(lang_frame, text="日本語", variable=self.lang_var, value="ja", bootstyle="primary").grid(row=0, column=1, padx=10)
        ttk.Radiobutton(lang_frame, text="英語", variable=self.lang_var, value="en", bootstyle="primary").grid(row=0, column=2, padx=10)

        ttk.Label(lang_frame, text="【声質 (Edge専用)】", font=("Helvetica", 10, "bold")).grid(row=1, column=0, pady=5, sticky="e")
        ttk.Radiobutton(lang_frame, text="男性 (Keita / Guy)", variable=self.gender_var, value="Male", bootstyle="primary").grid(row=1, column=1, padx=10)
        ttk.Radiobutton(lang_frame, text="女性 (Nanami / Aria)", variable=self.gender_var, value="Female", bootstyle="primary").grid(row=1, column=2, padx=10)

        # 3. Output Format
        format_frame = ttk.Labelframe(self.root, text="3. 出力形式の選択", padding=10)
        format_frame.pack(fill="x", pady=(0, 10))
        self.output_format_var = ttk.StringVar(value="HTML")
        ttk.Radiobutton(format_frame, text="音声のみ (MP3/WAV)", variable=self.output_format_var, value="MP3", bootstyle="primary").pack(side="left", padx=10)
        ttk.Radiobutton(format_frame, text="ブラウザ再生用・ハイライト付き (HTML) ※Edge専用", variable=self.output_format_var, value="HTML", bootstyle="primary").pack(side="left", padx=10)

        # 4. Text Input / File Load
        input_header_frame = ttk.Frame(self.root)
        input_header_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(input_header_frame, text="4. 読み上げたいテキスト (直接入力 or ファイル選択):", font=("Helvetica", 11, "bold")).pack(side="left")
        
        self.load_btn = ttk.Button(input_header_frame, text="📁 ファイルを選択", bootstyle="outline-primary", command=self.load_from_file)
        self.load_btn.pack(side="right", padx=5)

        self.clear_file_btn = ttk.Button(input_header_frame, text="✖ 選択解除", bootstyle="outline-danger", command=self.clear_file_selection, state="disabled")
        self.clear_file_btn.pack(side="right", padx=5)
        
        text_frame = ttk.Frame(self.root)
        text_frame.pack(fill="both", expand=True, pady=(5, 10))
        
        scrollbar = ttk.Scrollbar(text_frame, bootstyle="round")
        scrollbar.pack(side="right", fill="y")
        
        self.text_area = tk.Text(text_frame, height=8, font=("Helvetica", 11), yscrollcommand=scrollbar.set, bg="#2b2b2b", fg="#ffffff", insertbackground="white")
        self.text_area.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_area.yview)
        self.text_area.bind("<<Modified>>", self.on_text_modified)

        self.char_count_label = ttk.Label(self.root, text="現在の文字数: 0文字", font=("Helvetica", 10, "bold"), bootstyle="info")
        self.char_count_label.pack(anchor="e")

        # 5. Parameters
        self.param_frame = ttk.Labelframe(self.root, text="5. 変換パラメータ（自動調整 / 手動変更可）", padding=10)
        self.param_frame.pack(fill="x", pady=10)

        ttk.Label(self.param_frame, text="処理文字数 (チャンク):").grid(row=0, column=0, sticky="e", pady=5)
        self.chunk_var = ttk.StringVar(value="1000")
        self.chunk_entry = ttk.Entry(self.param_frame, textvariable=self.chunk_var, width=10)
        self.chunk_entry.grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(self.param_frame, text="待機時間 (最小) 秒:").grid(row=0, column=2, sticky="e", pady=5)
        self.wait_min_var = ttk.StringVar(value="1.0")
        self.wait_min_entry = ttk.Entry(self.param_frame, textvariable=self.wait_min_var, width=10)
        self.wait_min_entry.grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(self.param_frame, text="待機時間 (最大) 秒:").grid(row=1, column=2, sticky="e", pady=5)
        self.wait_max_var = ttk.StringVar(value="2.0")
        self.wait_max_entry = ttk.Entry(self.param_frame, textvariable=self.wait_max_var, width=10)
        self.wait_max_entry.grid(row=1, column=3, sticky="w", padx=5)
        
        ttk.Label(self.param_frame, text="再生速度 (倍速):").grid(row=2, column=0, sticky="e", pady=5)
        self.speed_var = ttk.StringVar(value="2.5")
        self.speed_entry = ttk.Combobox(self.param_frame, textvariable=self.speed_var, values=["1.0", "1.5", "2.0", "2.5", "3.0"], state="readonly", width=8)
        self.speed_entry.grid(row=2, column=1, sticky="w", padx=5)

        for entry in (self.chunk_entry, self.wait_min_entry, self.wait_max_entry):
            entry.bind("<KeyRelease>", self.disable_auto_adjust)

        self.reset_btn = ttk.Button(self.param_frame, text="自動調整に戻す", bootstyle="warning-outline", command=self.enable_auto_adjust, state="disabled")
        self.reset_btn.grid(row=1, column=0, columnspan=2, pady=5)

        # Progress and Status
        self.status_label = ttk.Label(self.root, text="待機中...", font=("Helvetica", 11, "bold"))
        self.status_label.pack(pady=(5, 5))
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=100, mode="determinate", bootstyle="success-striped")
        self.progress.pack(fill="x", pady=5)

        # 6. Start Button
        self.start_btn = ttk.Button(self.root, text="処理を開始して保存", bootstyle="success", command=self.start_processing)
        self.start_btn.pack(pady=15, fill="x")

        # 7. Error Log Area
        self.error_frame = ttk.Labelframe(self.root, text="7. エラーログ (問題発生時のみ出力されます)", padding=5, bootstyle="danger")
        self.error_frame.pack(fill="both", expand=True, pady=(0, 10))

        error_scroll = ttk.Scrollbar(self.error_frame)
        error_scroll.pack(side="right", fill="y")

        self.error_area = tk.Text(self.error_frame, height=4, font=("Consolas", 9), yscrollcommand=error_scroll.set, bg="#3b1c1c", fg="#ff9999", insertbackground="white")
        self.error_area.pack(side="left", fill="both", expand=True)
        error_scroll.config(command=self.error_area.yview)
        
        self.error_area.insert(tk.END, "※エラーは発生していません。")
        self.error_area.config(state="disabled")

    def load_from_file(self):
        filepath = filedialog.askopenfilename(
            parent=self.root,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="読み込むテキストファイルを選択してください"
        )
        if not filepath:
            return

        try:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="cp932") as f:
                    content = f.read()

            self.file_text = content
            self.text_area.config(state="normal")
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, f"【ファイル選択中】\n{filepath}\n\n※ファイルから直接読み込んで変換します。\n※動作を軽くするため、テキストのプレビューは省略されています。")
            self.text_area.config(state="disabled")

            self.clear_file_btn.config(state="normal")

            text_length = len(self.file_text)
            self.char_count_label.config(text=f"現在の文字数: {text_length:,} 文字 (ファイル)")
            
            if self.auto_adjust_enabled and text_length > 0:
                self.calculate_and_set_parameters(text_length)
            
            self.status_label.config(text="ファイルを選択しました。保存ボタンを押して変換を開始してください。", bootstyle="info")

        except Exception as e:
            self.logger.log("ファイル読み込みエラー", str(e))

    def clear_file_selection(self):
        self.file_text = None
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", tk.END)
        self.clear_file_btn.config(state="disabled")
        self.status_label.config(text="待機中...", bootstyle="default")
        self._update_text_info()

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
            self.char_count_label.config(bootstyle="danger", text=self.char_count_label.cget("text").replace(" (手動設定中)", "") + " (手動設定中)")

    def enable_auto_adjust(self):
        self.auto_adjust_enabled = True
        self.reset_btn.config(state="disabled")
        self._update_text_info()

    def update_status_cb(self, message: str, progress: float) -> None:
        """Callback to update status and progress bar from worker threads."""
        self.root.after(0, self._update_status_internal, message, progress)

    def _update_status_internal(self, message: str, progress: float) -> None:
        self.status_label.config(text=message, bootstyle="default")
        self.progress["value"] = progress

    def start_processing(self):
        self.sanitizer.load_rules()
        
        if self.file_text is not None:
            original_text = self.file_text.strip()
        else:
            original_text = self.text_area.get("1.0", "end-1c").strip()
            
        sanitized_text = self.sanitizer.sanitize(original_text)
            
        if not sanitized_text:
            # FIX: Messagebox.show_warning requires parent, title, message in ttkbootstrap (actually message, title)
            # Signature: Messagebox.show_warning(message, title="Warning", parent=None)
            Messagebox.show_warning("テキストを入力するか、ファイルを選択してください。", title="警告", parent=self.root)
            return

        engine_choice = self.engine_var.get()
        lang_choice = self.lang_var.get()
        gender_choice = self.gender_var.get()
        output_format = self.output_format_var.get()
        speed = float(self.speed_var.get())
        chunk_size = w_min = w_max = 0

        if output_format == "HTML" and engine_choice != "edge-tts":
            Messagebox.show_warning("HTML出力は Edge-TTS エンジンを選択している時のみ利用可能です。", title="警告", parent=self.root)
            return

        if engine_choice in ["gTTS", "edge-tts"]:
            try:
                chunk_size = int(self.chunk_var.get())
                w_min = float(self.wait_min_var.get())
                w_max = float(self.wait_max_var.get())
            except ValueError:
                self.logger.log("パラメータエラー", "待機時間やチャンク数には数値を入力してください。")
                return

        default_ext = ".mp3" if engine_choice in ["gTTS", "edge-tts"] else ".wav"
        file_types = [("Audio Files", "*.mp3 *.wav"), ("All Files", "*.*")]
        
        if output_format == "HTML":
            default_ext = ".html"
            file_types = [("HTML Files", "*.html"), ("All Files", "*.*")]
            
        current_time_str = datetime.now().strftime("%Y%m%d_%H%M_output") + default_ext
        
        save_path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=default_ext,
            initialfile=current_time_str,
            filetypes=file_types,
            title="保存先を選んでください"
        )
        
        if not save_path:
            return

        # Disable UI elements
        self.start_btn.config(state="disabled")
        self.load_btn.config(state="disabled")
        self.clear_file_btn.config(state="disabled")
        self.text_area.config(state="disabled")
        self.progress["value"] = 0
        self.logger.clear()

        self.status_label.config(text="[1/5] バックグラウンドスレッドを起動中...", bootstyle="default")
        self.root.update_idletasks()
        
        thread = threading.Thread(
            target=self.process_thread_wrapper, 
            args=(original_text, sanitized_text, engine_choice, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path, output_format, speed)
        )
        thread.daemon = True
        thread.start()

    def process_thread_wrapper(self, original_text, sanitized_text, engine_choice, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path, output_format, speed):
        """Wrapper to instantiate engine and catch global errors."""
        try:
            if engine_choice == "edge-tts":
                engine = EdgeTTSEngine(self.update_status_cb)
            elif engine_choice == "gTTS":
                engine = GTTSEngine(self.update_status_cb)
            else:
                engine = Pyttsx3Engine(self.update_status_cb)
                
            engine.process(original_text, sanitized_text, chunk_size, w_min, w_max, lang_choice, gender_choice, save_path, output_format=output_format, speed=speed)
            
            self.root.after(0, self.finish_processing, True, f"保存完了: {save_path}", None)
        except Exception as e:
            error_details = traceback.format_exc()
            self.root.after(0, self.finish_processing, False, str(e), error_details)

    def finish_processing(self, success, message, error_details):
        self.start_btn.config(state="normal")
        self.load_btn.config(state="normal")
        
        if self.file_text is None:
            self.text_area.config(state="normal")
        else:
            self.clear_file_btn.config(state="normal")
        
        if success:
            self.status_label.config(text="完了", bootstyle="info")
            self.progress["value"] = 100
            self.logger.clear()
            if save_path and save_path.endswith(".html"):
                import webbrowser
                webbrowser.open("file://" + save_path)
            # FIX: Messagebox.show_info(message, title="Info", parent=None)
            Messagebox.show_info(message, title="完了", parent=self.root)
        else:
            current_status = self.status_label.cget("text")
            self.status_label.config(text=f"処理停止 (エラー発生): {current_status}", bootstyle="danger")
            self.logger.log(message, error_details)
