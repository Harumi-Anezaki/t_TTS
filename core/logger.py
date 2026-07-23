import tkinter as tk
from typing import Optional

class UILogger:
    """
    Handles thread-safe logging to the UI Text widget.
    """
    def __init__(self, text_widget: tk.Text, root: tk.Tk):
        self.text_widget = text_widget
        self.root = root

    def log(self, summary: str, details: str = "") -> None:
        """
        Logs a message to the UI text widget in a thread-safe manner.
        
        Args:
            summary (str): The main summary of the log.
            details (str, optional): Detailed information, such as exception traces. Defaults to "".
        """
        # Ensure UI updates happen on the main thread
        self.root.after(0, self._log_internal, summary, details)

    def _log_internal(self, summary: str, details: str) -> None:
        """Internal method running on the main UI thread to update the widget."""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        
        message = f"【概要】\n{summary}"
        if details:
            message += f"\n\n【詳細な情報】\n{details}"
            
        self.text_widget.insert(tk.END, message)
        self.text_widget.config(state="disabled")
        self.text_widget.yview(tk.END)

    def clear(self) -> None:
        """Clears the log area."""
        self.root.after(0, self._clear_internal)
        
    def _clear_internal(self) -> None:
        """Internal method running on the main UI thread to clear the widget."""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, "※エラーは発生していません。")
        self.text_widget.config(state="disabled")
