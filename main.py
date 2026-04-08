"""
Screen Analyzer — Real-time Question Detector + AI Answerer
Main entry point that ties together screen capture, OCR, text analysis, AI answering, and GUI overlay.
"""

import threading
import time
import sys
import os

from capture import capture_screen
from ocr_engine import extract_lines_with_boxes, setup_tesseract
from text_analyzer import analyze_lines
from ai_answerer import ask_ai
from stealth_overlay import StealthOverlay


def load_api_key() -> str:
    """Load API key from config.env file."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")

    if not os.path.isfile(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in ("GEMINI_API_KEY", "GROQ_API_KEY", "API_KEY"):
                return value.strip()

    return None


class ScreenAnalyzer:
    """Main application controller."""

    def __init__(self, interval: float = 3.0, api_key: str = None):
        self.interval = interval
        self.api_key = api_key
        self.running = False
        self.overlay = StealthOverlay()
        self.analysis_thread = None
        self.last_question = None

    def _answer_question(self, question_context: str, options_data: list):
        """Ask AI and trigger the stealth hover proxy."""
        if not self.api_key:
            return

        # Build simple text list for the AI prompt
        options_text = [opt["text"] for opt in options_data]
        ai_result = ask_ai(question_context, options_text, self.api_key)

        respuesta = ai_result.get("respuesta")
        if not respuesta:
            return
            
        print(f"\n[AI] Contexto proporcionado ({len(question_context)} chars)")
        print(f"[AI] Respuesta: {respuesta}")

        # Find which OCR option matches the AI's answer
        correct_box = None
        # the AI answer might be exactly the option text, or contain the option text
        for opt in options_data:
            text = opt["text"].upper()
            resp = respuesta.upper()
            if text in resp or resp in text:
                correct_box = opt["box"]
                break
                
        # If no precise match, fallback to a softer match
        if not correct_box:
            for opt in options_data:
                # Check if just the first 3 chars match e.g. "A)"
                if opt["text"][:3].upper() in respuesta.upper():
                    correct_box = opt["box"]
                    break

        if correct_box:
            print(f"[STEALTH] Creando proxy invisible en {correct_box}")
            self.overlay.schedule(0, lambda: self.overlay.show_correct_answer_proxy(correct_box))

    def _analysis_loop(self):
        """Background thread: capture → OCR → analyze → answer → update StealthOverlay."""
        while self.running:
            try:
                image = capture_screen()
                # OCR Grouped by Lines with Bounding Boxes
                lines_data = extract_lines_with_boxes(image)
                # Analyze
                analysis = analyze_lines(lines_data)

                question = analysis.get("pregunta_detectada")
                if question and question != self.last_question:
                    self.last_question = question
                    options_data = analysis.get("opciones_detectadas", [])
                    print(f"\n[DETECTADO] Nueva pregunta:\n{question}")
                    
                    if options_data:
                        # Clear any existing proxy since screen changed
                        self.overlay.schedule(0, self.overlay.clear_proxy)
                        context = analysis.get("contexto_completo") or question
                        answer_thread = threading.Thread(
                            target=self._answer_question,
                            args=(context, options_data),
                            daemon=True
                        )
                        answer_thread.start()

            except Exception as e:
                print(f"[ERROR] {type(e).__name__}: {str(e)}")

            # Wait for next cycle
            for _ in range(int(self.interval * 10)):
                if not self.running:
                    return
                time.sleep(0.1)

    def start(self):
        """Start the analyzer."""
        print("[INFO] Screen Analyzer + AI (STEALTH MODE) - Iniciando...")

        if not setup_tesseract():
            print("\n❌ ERROR: Tesseract OCR no encontrado.")
            sys.exit(1)

        print("[OK] Tesseract encontrado.")

        if self.api_key:
            print(f"[OK] API key configurada: {self.api_key[:10]}...")
        else:
            print("[WARN] No hay API key. El programa detectará preguntas pero NO las responderá.")

        print(f"[INFO] Intervalo de captura: {self.interval}s")
        print("[INFO] Modo SIGILOSO activo. No habrá ventana flotante.")
        print("[INFO] El mouse se convertirá en un dedo (👆) cuando pases sobre la respuesta correcta.\n")

        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

        # Run GUI loop strictly to keep Tkinter / Proxy alive
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\n[INFO] Screen Analyzer cerrado.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="🔍 Screen Analyzer + AI - Detector y respondedor de preguntas en tiempo real"
    )
    parser.add_argument(
        "-i", "--interval",
        type=float,
        default=3.0,
        help="Segundos entre cada captura (default: 3.0)"
    )
    parser.add_argument(
        "-k", "--api-key",
        type=str,
        default=None,
        help="Gemini API key (también puede configurarse en config.env)"
    )
    args = parser.parse_args()

    # Load API key: CLI > config.env
    api_key = args.api_key or load_api_key()

    analyzer = ScreenAnalyzer(interval=args.interval, api_key=api_key)
    analyzer.start()


if __name__ == "__main__":
    main()
