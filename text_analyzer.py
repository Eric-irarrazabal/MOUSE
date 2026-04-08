"""
Text Analyzer Module
Analyzes extracted text to detect questions, options, and filter noise.
"""

import re
import json


# Common UI noise to filter out
NOISE_PATTERNS = [
    r"^(home|inicio|menu|menú|settings|configuración|login|sign in|sign up|log out)$",
    r"^(search|buscar|cancel|cancelar|ok|accept|aceptar|close|cerrar|submit|enviar)$",
    r"^(next|siguiente|previous|anterior|back|atrás|skip|omitir|continue|continuar)$",
    r"^(share|compartir|like|follow|subscribe|suscribir|download|descargar)$",
    r"^(©|copyright|all rights reserved|todos los derechos|privacy|política).*$",
    r"^\s*[\|\-\=\+\#\*]{3,}\s*$",  # Decorative lines
    r"^.{1,3}$",  # Very short lines (likely UI elements)
    r"^(dashboard|crear|quiz|q\s?\d+).*$" # Quiz app specific noise
]

# Patterns indicating a question
QUESTION_INDICATORS_ES = [
    r"¿[^?]+\?",  # Spanish question marks
    r"cuál\s", r"qué\s", r"cómo\s", r"dónde\s", r"por\s+qué",
    r"quién\s", r"cuándo\s", r"cuánto", r"cuál\s+es", r"qué\s+es",
    r"selecciona", r"elige", r"escoge", r"indica", r"marca",
]

QUESTION_INDICATORS_EN = [
    r"\w+.*\?",  # Ends with question mark
    r"^which\s", r"^what\s", r"^how\s", r"^where\s", r"^why\s",
    r"^who\s", r"^when\s", r"^is\s+\w+", r"^are\s+\w+", r"^do\s+\w+",
    r"^does\s+\w+", r"^can\s+\w+", r"^select\s", r"^choose\s", r"^pick\s",
]

# Patterns indicating answer options
OPTION_PATTERNS = [
    r"^\s*[a-eA-E]\)\s*.+",       # a) option text
    r"^\s*[a-eA-E]\.\s*.+",       # a. option text
    r"^\s*[a-eA-E]\-\s*.+",       # a- option text
    r"^\s*[a-eA-E]\s+.+",         # a option text (like "A 1980")
    r"^\s*[1-5]\)\s*.+",          # 1) option text
    r"^\s*[1-5]\.\s*.+",          # 1. option text
    r"^\s*[•●○]\s*.+",            # bullet points
    r"^\s*[\u2610\u2611\u2612]\s*.+",  # checkboxes
    r"^\s*\[\s?\]\s*.+",          # [ ] option
    r"^\s*\(\s?\)\s*.+",          # ( ) option
]


def _is_noise(line: str) -> bool:
    """Check if a line is UI noise."""
    clean = line.strip().lower()
    if not clean:
        return True
    # Filter out score-like strings "00000" or "Q 5 / 10"
    if re.match(r"^0+$", clean) or re.match(r"^q\s*\d+\s*/\s*\d+$", clean):
        return True
    
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, clean, re.IGNORECASE):
            return True
    return False


def _clean_text(raw_text: str) -> list[str]:
    """Remove noise and return clean lines."""
    lines = raw_text.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not _is_noise(stripped):
            clean_lines.append(stripped)
    return clean_lines


def _find_question(lines: list[str]) -> str | None:
    """Find the most likely question in the text (handles multiline)."""
    all_patterns = QUESTION_INDICATORS_ES + QUESTION_INDICATORS_EN
    candidates = []

    for i, line in enumerate(lines):
        score: int = 0
        for pattern in all_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                score += 1
        # Bonus for question marks
        if "?" in line:
            score += 3
        if "¿" in line:
            score += 3

        if score > 0:
            candidates.append((score, i, line))

    if not candidates:
        # Fallback: if no question mark, but options exist, just return the line before options
        for i, line in enumerate(lines):
            for pattern in OPTION_PATTERNS:
                if re.match(pattern, line):
                    if i > 0:
                        return lines[i-1]
        return None

    # Sort by score descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_idx = candidates[0][1]
    best_line = candidates[0][2]

    # Try to combine with previous lines if they seem part of the same sentence
    question_lines = [best_line]
    
    # Go backwards to collect the start of the question
    # Only if the best_line doesn't already start with '¿'
    if not best_line.strip().startswith("¿"):
        curr_idx = best_idx - 1
        while curr_idx >= 0:
            prev_line = lines[curr_idx]
            # Stop merging if it's an option or very short
            if any(re.match(p, prev_line) for p in OPTION_PATTERNS):
                break
            if len(prev_line) < 3:
                break
                
            question_lines.insert(0, prev_line)
            
            # Stop if we found the start of the question ('¿')
            if "¿" in prev_line:
                break
                
            curr_idx -= 1
        
    # Go forwards to collect the end of the question (if split across multiple lines, e.g. options come later)
    # Only if the best line didn't end in '?'
    if "?" not in best_line:
        curr_idx = best_idx + 1
        while curr_idx < len(lines):
            next_line = lines[curr_idx]
            if any(re.match(p, next_line) for p in OPTION_PATTERNS):
                break
            
            question_lines.append(next_line)
            if "?" in next_line:
                break
                
            curr_idx += 1

    return " ".join(question_lines)


def _find_options(lines: list[str]) -> list[str]:
    """Find answer options in the text."""
    options = []
    for line in lines:
        for pattern in OPTION_PATTERNS:
            if re.match(pattern, line):
                options.append(line.strip())
                break
    return options


def _determine_clarity(question: str | None, options: list[str]) -> str:
    """Determine how clear the question is."""
    if not question:
        return "no_detectada"
    if "?" in question or "¿" in question:
        return "clara"
    if options:
        return "clara"
    return "ambigua"


def _clean_lines_data(lines_data: list[dict]) -> list[dict]:
    """Remove noise and return clean line objects."""
    clean_lines = []
    for line_obj in lines_data:
        if not _is_noise(line_obj["text"]):
            clean_lines.append(line_obj)
    return clean_lines


def _find_question_from_data(lines_data: list[dict]) -> str | None:
    """Find the specific sentence that forms the question."""
    if not lines_data:
        return None
    texts = [obj["text"] for obj in lines_data]
    return _find_question(texts)


def _find_options_from_data(lines_data: list[dict]) -> list[dict]:
    """Find answer options in the text and return them with bounding boxes."""
    options = []
    import re
    for line_obj in lines_data:
        text = line_obj["text"]
        for pattern in OPTION_PATTERNS:
            if re.match(pattern, text):
                options.append({
                    "text": text.strip(),
                    "box": {
                        "x": line_obj["left"],
                        "y": line_obj["top"],
                        "w": line_obj["width"],
                        "h": line_obj["height"]
                    }
                })
                break
    return options


def analyze_lines(lines_data: list[dict]) -> dict:
    if not lines_data:
        return {
            "pregunta_detectada": None,
            "contexto_completo": None,
            "opciones_detectadas": [],
            "interpretacion_visual": "Pantalla vacía o sin texto legible."
        }

    clean_lines_data = _clean_lines_data(lines_data)

    if not clean_lines_data:
        return {
            "pregunta_detectada": None,
            "contexto_completo": None,
            "opciones_detectadas": [],
            "interpretacion_visual": "Solo se detectó texto de interfaz."
        }

    options_data = _find_options_from_data(clean_lines_data)
    
    option_texts = [opt["text"] for opt in options_data]
    non_option_data = [obj for obj in clean_lines_data if obj["text"] not in option_texts]
    
    question = _find_question_from_data(non_option_data)
    
    # NEW: Capture full static context for AI
    full_context_texts = [obj["text"] for obj in non_option_data]
    context = "\n".join(full_context_texts) if full_context_texts else None
    
    clarity = _determine_clarity(question, option_texts)

    return {
        "pregunta_detectada": question,
        "contexto_completo": context,
        "opciones_detectadas": options_data,
        "claridad": clarity
    }
