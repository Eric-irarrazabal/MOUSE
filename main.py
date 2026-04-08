"""
Screen Analyzer — Real-time Question Detector + AI Answerer
Main entry point: stealth mode only. No visible overlay.
The cursor changes to a hand when hovering over the correct answer.
"""

import threading
import time
import sys
import os

from capture import capture_screen
from ocr_engine import extract_lines_with_boxes, setup_tesseract
from text_analyzer import analyze_lines
from ai_answerer import ask_ai, match_to_option_index
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
    """Main application controller — stealth mode only."""

    def __init__(self, interval: float = 3.0, api_key: str = None):
        self.interval = interval
        self.api_key = api_key
        self.running = False
        self.overlay = StealthOverlay()
        self.analysis_thread = None
        self.last_question = None

    def _answer_question(self, question_context: str, options_data: list):
        """Ask AI with two-pass verification and activate stealth proxy on correct answer."""
        if not self.api_key:
            return

        options_text = [opt["text"] for opt in options_data]
        ai_result = ask_ai(question_context, options_text, self.api_key)

        respuesta = ai_result.get("respuesta")
        confianza = ai_result.get("confianza", 0)

        if not respuesta:
            return

        print(f"\n[AI] Respuesta: {respuesta}")
        print(f"[AI] Confianza: {confianza}%")
        print(f"[AI] Pasadas: {ai_result.get('pass_count', 1)}")

        if ai_result.get("explicacion"):
            print(f"[AI] Explicacion: {ai_result['explicacion'][:150]}...")

        # Only activate stealth proxy if confidence is high enough
        if confianza < 85:
            print(f"[STEALTH] Confianza insuficiente ({confianza}%), proxy NO activado")
            return

        # Use precise matching
        match_idx = match_to_option_index(respuesta, options_text)

        if match_idx is not None:
            correct_box = options_data[match_idx]["box"]
            print(f"[STEALTH] Proxy activado en opcion: {options_text[match_idx]}")
            self.overlay.schedule(
                0, lambda b=correct_box: self.overlay.show_correct_answer_proxy(b)
            )
        else:
            print(f"[STEALTH] No se pudo mapear respuesta a opcion")

    def _analysis_loop(self):
        """Background thread: capture -> OCR -> analyze -> answer -> stealth proxy."""
        while self.running:
            try:
                image = capture_screen()
                lines_data = extract_lines_with_boxes(image)
                analysis = analyze_lines(lines_data)

                question = analysis.get("pregunta_detectada")
                if question and question != self.last_question:
                    self.last_question = question
                    options_data = analysis.get("opciones_detectadas", [])
                    print(f"\n[DETECTADO] Pregunta: {question}")
                    print(f"[DETECTADO] Opciones: {[o['text'] for o in options_data]}")

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
        """Start the analyzer in stealth mode."""
        print("[INFO] Screen Analyzer + AI (STEALTH MODE) - Iniciando...")

        if not setup_tesseract():
            print("\nERROR: Tesseract OCR no encontrado.")
            sys.exit(1)

        print("[OK] Tesseract encontrado.")

        if self.api_key:
            print(f"[OK] API key configurada: {self.api_key[:10]}...")
        else:
            print("[WARN] No hay API key. Detectara preguntas pero NO las respondera.")

        print(f"[INFO] Intervalo de captura: {self.interval}s")
        print("[INFO] Modo SIGILOSO activo. No hay ventana flotante.")
        print("[INFO] El cursor cambiara a mano sobre la respuesta correcta.\n")

        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

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
        description="Screen Analyzer + AI - Detector y respondedor de preguntas en tiempo real"
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
        help="API key (Gemini o Groq, tambien puede configurarse en config.env)"
    )
    args = parser.parse_args()

    api_key = args.api_key or load_api_key()

    analyzer = ScreenAnalyzer(interval=args.interval, api_key=api_key)
    analyzer.start()


if __name__ == "__main__":
    main()
