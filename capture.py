"""
Screen Capture Module
Captures the screen using mss for fast, cross-platform screenshots.
"""

import mss
import mss.tools
from PIL import Image


def capture_screen(monitor_number: int = 1, region: dict = None) -> Image.Image:
    """
    Capture the screen and return a PIL Image.

    Args:
        monitor_number: Which monitor to capture (1 = primary, 2 = secondary, etc.)
        region: Optional dict with keys 'left', 'top', 'width', 'height' to capture a specific region.

    Returns:
        PIL Image of the captured screen.
    """
    with mss.mss() as sct:
        if region:
            monitor = region
        else:
            monitor = sct.monitors[monitor_number]

        screenshot = sct.grab(monitor)
        # Convert to PIL Image (BGRA -> RGB)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img


def capture_screen_bytes(monitor_number: int = 1) -> bytes:
    """
    Capture screen and return as PNG bytes (useful for saving/streaming).
    """
    import io
    img = capture_screen(monitor_number)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


if __name__ == "__main__":
    img = capture_screen()
    print(f"Captured screen: {img.size}")
    img.save("test_capture.png")
    print("Saved to test_capture.png")
