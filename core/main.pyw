import sys
import os
import ctypes
from ctypes import wintypes
import ttkbootstrap as ttk

# Add core directory to python path if not running from root
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.ui import TTSUI

def configure_dpi_awareness():
    """Configures Windows DPI awareness to prevent blurry fonts and incorrect scaling."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def get_work_area():
    """Returns the usable desktop area (excluding taskbar) as (x, y, width, height)."""
    try:
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        # Fallback if Windows API fails
        import tkinter as tk
        temp_root = tk.Tk()
        w = temp_root.winfo_screenwidth()
        h = temp_root.winfo_screenheight()
        temp_root.destroy()
        return 0, 0, w, h

def main():
    # 1. Setup DPI awareness
    configure_dpi_awareness()
    
    # 2. Initialize application root
    root = ttk.Window(themename="darkly")
    root.title("TTS")
    
    # 3. Calculate and set window geometry (snap to left half of work area)
    work_x, work_y, work_w, work_h = get_work_area()
    half_width = work_w // 2
    
    # Apply geometry and padding
    root.geometry(f"{half_width}x{work_h}+{work_x}+{work_y}")
    root.configure(padx=20, pady=20)
    
    # 4. Initialize UI logic
    app = TTSUI(root)
    
    # 5. Start main loop
    root.mainloop()

if __name__ == "__main__":
    main()