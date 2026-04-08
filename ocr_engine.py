"""
OCR Engine Module
Extracts text from images using Tesseract OCR.
"""

import os
import shutil
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract


def _find_tesseract():
    """Auto-detect Tesseract installation on Windows."""
    # Check if already in PATH
    if shutil.which("tesseract"):
        return shutil.which("tesseract")

    # Common Windows installation paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
    ]

    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


def setup_tesseract():
    """Configure Tesseract path. Returns True if found."""
    tesseract_path = _find_tesseract()
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return True
    return False


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR results.
    - Convert to grayscale
    - Increase contrast
    - Sharpen
    - Scale up small images
    """
    # Convert to grayscale
    img = image.convert("L")

    # Scale up if small (improves OCR accuracy)
    width, height = img.size
    if width < 1000:
        scale = 2
        img = img.resize((width * scale, height * scale), Image.LANCZOS)

    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    return img


def extract_text(image: Image.Image, lang: str = "spa+eng", preprocess: bool = True) -> str:
    """
    Extract text from a PIL Image using Tesseract OCR.

    Args:
        image: PIL Image to extract text from.
        lang: Language(s) for OCR. Default: Spanish + English.
        preprocess: Whether to preprocess the image for better results.

    Returns:
        Extracted text as a string.
    """
    if preprocess:
        image = preprocess_image(image)

    try:
        text = pytesseract.image_to_string(image, lang=lang)
    except pytesseract.TesseractNotFoundError:
        # Try to find and configure Tesseract
        if setup_tesseract():
            text = pytesseract.image_to_string(image, lang=lang)
        else:
            raise RuntimeError(
                "Tesseract OCR no encontrado. Instálalo desde:\n"
                "https://github.com/UB-Mannheim/tesseract/wiki\n"
                "Asegúrate de agregar el idioma español durante la instalación."
            )

    return text.strip()


def extract_lines_with_boxes(image: Image.Image, lang: str = "spa+eng", preprocess: bool = True) -> list:
    """
    Extract text grouped by lines, including bounding boxes for each line.
    Returns:
        List of dicts: [{"text": str, "left": int, "top": int, "width": int, "height": int, "conf": float}]
    """
    if preprocess:
        # Preprocess modifies image scale, so boxes need to be scaled back.
        # However, if we just keep the image as is or apply non-scaling preprocessing, it's easier.
        img = image.convert("L")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)
    else:
        img = image

    if not setup_tesseract():
        raise RuntimeError("Tesseract OCR no encontrado.")

    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    
    # data has 'block_num', 'par_num', 'line_num', 'word_num', 'text', 'left', 'top', 'width', 'height', 'conf'
    lines_map = {}
    
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text:
            continue
            
        conf = float(data['conf'][i])
        if conf < 10:  # Ignore very low confidence noise
            continue
            
        block = data['block_num'][i]
        par = data['par_num'][i]
        line = data['line_num'][i]
        
        # Unique identifier for the physical line
        line_id = f"{block}_{par}_{line}"
        
        l = data['left'][i]
        t = data['top'][i]
        w = data['width'][i]
        h = data['height'][i]
        r = l + w
        b = t + h
        
        if line_id not in lines_map:
            lines_map[line_id] = {
                "text_parts": [text],
                "left": l, "top": t, "right": r, "bottom": b,
                "conf_sum": conf, "count": 1
            }
        else:
            lines_map[line_id]["text_parts"].append(text)
            lines_map[line_id]["left"] = min(lines_map[line_id]["left"], l)
            lines_map[line_id]["top"] = min(lines_map[line_id]["top"], t)
            lines_map[line_id]["right"] = max(lines_map[line_id]["right"], r)
            lines_map[line_id]["bottom"] = max(lines_map[line_id]["bottom"], b)
            lines_map[line_id]["conf_sum"] += conf
            lines_map[line_id]["count"] += 1
            
    result = []
    for line_info in lines_map.values():
        result.append({
            "text": " ".join(line_info["text_parts"]),
            "left": line_info["left"],
            "top": line_info["top"],
            "width": line_info["right"] - line_info["left"],
            "height": line_info["bottom"] - line_info["top"],
            "conf": line_info["conf_sum"] / line_info["count"]
        })
        
    return result


if __name__ == "__main__":
    from capture import capture_screen

    if not setup_tesseract():
        print("ERROR: Tesseract no encontrado.")
    else:
        print("Tesseract encontrado. Capturando pantalla...")
        img = capture_screen()
        text = extract_text(img)
        print(f"Texto extraído ({len(text)} chars):")
        print(text[:500])
