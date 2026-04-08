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


def load_api_key() -> str | None:
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

        import re
        def clean_text(s): 
            return re.sub(r'[^A-Z0-9]', '', s.upper())
            
        correct_box = None
        c_resp = clean_text(respuesta)
        
        # 1. Intentar limpiar puntuación y buscar coincidencias completas
        for opt in options_data:
            c_text = clean_text(opt["text"])
            if c_text and c_resp and (c_text in c_resp or c_resp in c_text):
                correct_box = opt["box"]
                break
                
        # 2. Si no coincide, intentar buscar la primera letra (opción)
        if not correct_box:
            # Capturar 'A', 'B', '1', etc. al inicio de la respuesta de la IA
            m_resp = re.search(r'^([A-E1-5])\b', respuesta.strip().upper())
            if m_resp:
                target_letter = m_resp.group(1)
                for opt in options_data:
                    # Capturar 'A)', 'A.', 'A -' del OCR
                    m_opt = re.search(r'^([A-E1-5])[\)\.\-\s]', opt["text"].strip().upper())
                    if m_opt and m_opt.group(1) == target_letter:
                        correct_box = opt["box"]
                        break
                        
        # 3. Nivel de emergencia, buscar si la letra suelta está al principio del texto fallido del OCR
        if not correct_box and len(respuesta.strip()) > 0:
            target_letter = respuesta.strip()[0].upper()
            if target_letter in "ABCDE12345":
                for opt in options_data:
                    if opt["text"].strip().upper().startswith(target_letter):
                        correct_box = opt["box"]
                        break

        if correct_box:
            print(f"[STEALTH] ¡Encontró la respuesta exacta! Resaltando en azul ({correct_box})")
            self.overlay.schedule(0, lambda: self.overlay.show_correct_answer_proxy(correct_box))
        else:
            print(f"[STEALTH] No se pudo machear el texto OCR con la respuesta '{respuesta}'. Mostrando rectangulo azul de aviso en esquina superior.")
            # Crear una cajita fallback azul arriba a la izquierda para demostrar que la IA respondió
            fallback_box = {"x": 50, "y": 50, "w": 40, "h": 40}
            self.overlay.schedule(0, lambda: self.overlay.show_correct_answer_proxy(fallback_box))

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
        print("[INFO] El mouse se convertirá en una mano cuando pases sobre la respuesta correcta.\n")

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
