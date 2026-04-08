"""
Text Analyzer Module
Analyzes extracted text to detect questions, options, and filter noise.
Aggressive noise filtering for browser UI, URLs, app names, taskbar, etc.
"""

import re


# ═══════════════════════════════════════════════════════
# NOISE FILTERING — very aggressive to isolate quiz content
# ═══════════════════════════════════════════════════════

NOISE_WORDS_EXACT = {
    # Browser / OS UI
    "home", "inicio", "menu", "settings", "configuracion", "login",
    "sign in", "sign up", "log out", "search", "buscar", "cancel",
    "cancelar", "ok", "accept", "aceptar", "close", "cerrar", "submit",
    "enviar", "next", "siguiente", "previous", "anterior", "back",
    "skip", "omitir", "continue", "continuar", "share", "compartir",
    "like", "follow", "subscribe", "suscribir", "download", "descargar",
    # App names (bookmarks bar, tabs)
    "youtube", "gmail", "github", "claude", "chatgpt", "instagram",
    "facebook", "twitter", "tiktok", "discord", "reddit", "whatsapp",
    "telegram", "spotify", "netflix", "amazon", "google", "bing",
    "outlook", "server", "vivo", "ava", "epic",
    # Our own app text (prevent self-reading feedback)
    "screen analyzer", "pregunta detectada", "opciones detectadas",
    "respuesta ia", "confianza", "esperando pregunta", "esperando captura",
    "consultando ia", "activo", "pausado", "pausar", "reanudar", "salir",
    "clara", "ambigua", "no detectada", "verificado",
    # Taskbar items
    "esp", "laa", "buscar en windows",
    # Common noise
    "dashboard", "crear quiz",
}

NOISE_REGEX_PATTERNS = [
    r"^\s*[\|\-\=\+\#\*\_]{3,}\s*$",       # Decorative lines
    r"^.{1,3}$",                             # Very short (1-3 chars)
    r"^0+$",                                 # Score zeros "00000"
    r"^q\s*\d+\s*/\s*\d+$",                 # Quiz counter "Q 7 / 10"
    r"^q\s*\d+\s*/\s*\d+",                  # Quiz counter variations
    r"^\d{1,2}\s*/\s*\d{1,2}$",             # "7 / 10" or "7/10"
    r"https?://",                            # URLs
    r"www\.",                                # URLs without http
    r"\.(com|org|net|io|app|dev|vercel)\b",  # Domain extensions
    r"^\s*©",                                # Copyright
    r"all rights reserved",                  # Copyright English
    r"todos los derechos",                   # Copyright Spanish
    r"privacy|politica de privacidad",       # Privacy
    r"cookie",                               # Cookie notices
    r"generador de video",                   # Ad text
    r"made for learning",                    # Footer text
    r"^\s*@\s*\w",                           # Social handles
    r"^\s*[A-Z]{2,}\s*$",                   # Single ALL-CAPS word (YOUTUBE, GMAIL, etc.)
    r"^\d{2}:\d{2}$",                       # Time "17:25"
    r"^\d{2}-\d{2}-\d{4}$",                # Date "08-04-2026"
    r"^\d{2}/\d{2}/\d{4}$",                # Date "08/04/2026"
    r"^[\d\s\-\(\)\+]+$",                   # Phone numbers
    r"sin restricciones",                    # Ad text
    r"crea videos",                          # Ad text
    r"cinematograficos",                     # Ad text
    r"^\s*\d{1,3}\s*$",                     # Standalone numbers (scores, page numbers)
    r"^\s*[A-Z][a-z]*\s*$",                 # Single capitalized word ("Dashboard", "Claude")
    r"build\s+scre",                         # Tab fragment
    r"user\d*!",                             # Tab fragments like "USER1!"
    r"eric.irar",                            # Username fragments
]


def _is_noise(line: str) -> bool:
    """Check if a line is UI noise that should be filtered out."""
    clean = line.strip()
    if not clean:
        return True

    lower = clean.lower()

    # Exact match against known noise words
    if lower in NOISE_WORDS_EXACT:
        return True

    # Check if line starts with known noise (partial match)
    for noise in NOISE_WORDS_EXACT:
        if lower == noise:
            return True

    # Regex patterns
    for pattern in NOISE_REGEX_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return True

    # Lines that are just symbols/punctuation (no letters at all)
    if not re.search(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ¿¡]', clean):
        return True

    # Very long lines without question marks are likely concatenated noise
    if len(clean) > 200 and '?' not in clean and '¿' not in clean:
        return True

    return False


# ═══════════════════════════════════════════════════════
# QUESTION DETECTION
# ═══════════════════════════════════════════════════════

QUESTION_INDICATORS_ES = [
    r"¿[^?]+\?",
    r"cuál\b", r"qué\b", r"cómo\b", r"dónde\b", r"por\s+qué",
    r"quién\b", r"cuándo\b", r"cuánto", r"cuál\s+es", r"qué\s+es",
    r"selecciona", r"elige", r"escoge", r"indica\b", r"marca\b",
    r"cual\b", r"que\b.*\?",  # Without accents (OCR often misses them)
    r"como\b.*\?", r"donde\b.*\?", r"quien\b.*\?",
]

QUESTION_INDICATORS_EN = [
    r"\w+.*\?$",
    r"^which\s", r"^what\s", r"^how\s", r"^where\s", r"^why\s",
    r"^who\s", r"^when\s", r"^is\s+\w+", r"^are\s+\w+", r"^do\s+\w+",
    r"^does\s+\w+", r"^can\s+\w+", r"^select\s", r"^choose\s", r"^pick\s",
]


# ═══════════════════════════════════════════════════════
# OPTION DETECTION
# ═══════════════════════════════════════════════════════

OPTION_PATTERNS = [
    r"^\s*[a-eA-E]\)\s*.+",       # a) option text
    r"^\s*[a-eA-E]\.\s*.+",       # a. option text
    r"^\s*[a-eA-E]\-\s*.+",       # a- option text
    r"^\s*[a-eA-E]\s+[A-Z].+",    # A Maestro Roshi (letter + capitalized word)
    r"^\s*[1-5]\)\s*.+",          # 1) option text
    r"^\s*[1-5]\.\s*.+",          # 1. option text
    r"^\s*[•●○]\s*.+",            # bullet points
    r"^\s*[\u2610\u2611\u2612]\s*.+",  # checkboxes
    r"^\s*\[\s?\]\s*.+",          # [ ] option
    r"^\s*\(\s?\)\s*.+",          # ( ) option
]


def _find_question(lines: list) -> str | None:
    """Find the most likely question in the text (handles multiline)."""
    all_patterns = QUESTION_INDICATORS_ES + QUESTION_INDICATORS_EN
    candidates = []

    for i, line in enumerate(lines):
        score = 0
        for pattern in all_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                score += 1
        # Heavy bonus for Spanish question marks
        if "?" in line:
            score += 5
        if "¿" in line:
            score += 5
        # Bonus for longer lines (more likely to be actual content)
        if len(line) > 20:
            score += 1
        if len(line) > 50:
            score += 1

        if score > 0:
            candidates.append((score, i, line))

    if not candidates:
        # Fallback: if no question mark, but options exist, return the line before options
        for i, line in enumerate(lines):
            for pattern in OPTION_PATTERNS:
                if re.match(pattern, line):
                    if i > 0:
                        return lines[i - 1]
        return None

    # Sort by score descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_idx = candidates[0][1]
    best_line = candidates[0][2]

    # Try to combine with adjacent lines for multi-line questions
    question_lines = [best_line]

    # Go backwards to collect the start of the question
    if not best_line.strip().startswith("¿"):
        curr_idx = best_idx - 1
        while curr_idx >= 0:
            prev_line = lines[curr_idx]
            if any(re.match(p, prev_line) for p in OPTION_PATTERNS):
                break
            if len(prev_line) < 3:
                break
            question_lines.insert(0, prev_line)
            if "¿" in prev_line:
                break
            curr_idx -= 1

    # Go forwards to collect the end of the question
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


def _find_options(lines: list) -> list:
    """Find answer options in the text."""
    options = []
    for line in lines:
        for pattern in OPTION_PATTERNS:
            if re.match(pattern, line):
                options.append(line.strip())
                break
    return options


def _determine_clarity(question: str | None, options: list) -> str:
    """Determine how clear the question is."""
    if not question:
        return "no_detectada"
    if "?" in question or "¿" in question:
        return "clara"
    if options:
        return "clara"
    return "ambigua"


def _clean_lines_data(lines_data: list) -> list:
    """Remove noise and return clean line objects."""
    clean_lines = []
    for line_obj in lines_data:
        if not _is_noise(line_obj["text"]):
            clean_lines.append(line_obj)
    return clean_lines


def _find_question_from_data(lines_data: list) -> str | None:
    """Find the specific sentence that forms the question."""
    if not lines_data:
        return None
    texts = [obj["text"] for obj in lines_data]
    return _find_question(texts)


def _find_options_from_data(lines_data: list) -> list:
    """Find answer options in the text and return them with bounding boxes."""
    options = []
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


def analyze_lines(lines_data: list) -> dict:
    if not lines_data:
        return {
            "pregunta_detectada": None,
            "contexto_completo": None,
            "opciones_detectadas": [],
            "claridad": "no_detectada"
        }

    clean_lines_data = _clean_lines_data(lines_data)

    if not clean_lines_data:
        return {
            "pregunta_detectada": None,
            "contexto_completo": None,
            "opciones_detectadas": [],
            "claridad": "no_detectada"
        }

    options_data = _find_options_from_data(clean_lines_data)

    option_texts = [opt["text"] for opt in options_data]
    non_option_data = [obj for obj in clean_lines_data if obj["text"] not in option_texts]

    question = _find_question_from_data(non_option_data)

    # Full context for AI (non-option text)
    full_context_texts = [obj["text"] for obj in non_option_data]
    context = "\n".join(full_context_texts) if full_context_texts else None

    clarity = _determine_clarity(question, option_texts)

    return {
        "pregunta_detectada": question,
        "contexto_completo": context,
        "opciones_detectadas": options_data,
        "claridad": clarity
    }
