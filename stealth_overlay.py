"""
Stealth Overlay Module (Canvas Cracked Style)
Creates an invisible, transparent widget over the correct answer.
When hovered, it automatically changes the mouse to a hand cursor.
When clicked, it clicks the actual browser element underneath.
"""

import tkinter as tk
import pyautogui
import threading
import time
import ctypes

# Force DPI awareness so Tkinter uses physical display pixels (matching MSS/OCR)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class StealthOverlay:
    def __init__(self):
        self.root = tk.Tk()
        # Make the main window completely hidden
        self.root.withdraw()
        
        self.proxy_window = None
        self.is_active = True
        
    def show_correct_answer_proxy(self, box: dict):
        """
        Creates an invisible TopLevel window exactly over the given bounding box.
        """
        # If proxy already exists, update geometry or destroy
        self.clear_proxy()
            
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        
        # Quiz buttons usually span wide horizontally and have some vertical padding.
        # Tesseract only gives the coordinates of the text itself.
        pad_left = 30
        pad_right = 200  # Expand heavily to the right
        pad_y = 15
        
        px = max(0, x - pad_left)
        py = max(0, y - pad_y)
        pw = w + pad_left + pad_right
        ph = h + (pad_y * 2)
        
        self.proxy_window = tk.Toplevel(self.root)
        self.proxy_window.geometry(f"{pw}x{ph}+{px}+{py}")
        self.proxy_window.overrideredirect(True)
        self.proxy_window.attributes("-topmost", True)
        
        # Make the proxy window catch mouse events by having a slight alpha
        # Hacer que la ventana proxy sea ligeramente visible para demostrar que la IA sabe la respuesta
        self.proxy_window.attributes("-transparentcolor", "")
        self.proxy_window.attributes("-alpha", 0.15)  # 15% opacidad para que se vea claramente el resaltado
        self.proxy_window.configure(bg="blue")  # Un bloque azul tenue sobre el texto correcto

        # Set cursor to hand
        self.proxy_window.config(cursor="hand2")
        
        def on_click(e):
            # 1. Hide the proxy instantly
            self.clear_proxy()
            
            # 2. Force OS to update
            self.root.update()
            time.sleep(0.05)
            
            # 3. Simulate true click exactly where mouse is
            mx, my = pyautogui.position()
            pyautogui.click(mx, my)

        self.proxy_window.bind("<Button-1>", on_click)
        
    def clear_proxy(self):
        if self.proxy_window:
            self.proxy_window.destroy()
            self.proxy_window = None

    def run(self):
        self.root.mainloop()

    def schedule(self, ms, func):
        self.root.after(ms, func)
