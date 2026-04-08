"""
GUI Overlay Module
Floating overlay window that displays detected questions, AI answers,
and confidence levels in real-time.
"""

import tkinter as tk
from tkinter import font as tkfont


class OverlayWindow:
    """Semi-transparent floating window that shows detected questions and AI answers."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Screen Analyzer")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.93)
        self.root.configure(bg="#1a1a2e")
        self.root.geometry("520x580+50+50")
        self.root.resizable(True, True)

        # Enable window dragging
        self._drag_data = {"x": 0, "y": 0}

        # Fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.body_font = tkfont.Font(family="Segoe UI", size=10)
        self.answer_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        self.status_font = tkfont.Font(family="Segoe UI", size=9, slant="italic")
        self.conf_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")

        self._build_ui()

        # State
        self.is_paused = False
        self.on_pause_callback = None
        self.on_resume_callback = None

    def _build_ui(self):
        """Build the overlay UI."""
        colors = {
            "bg": "#1a1a2e",
            "header": "#16213e",
            "card": "#0f3460",
            "accent": "#e94560",
            "text": "#eaeaea",
            "text_dim": "#a0a0b0",
            "success": "#53d769",
            "warning": "#ffcc00",
            "option_bg": "#162447",
            "answer_bg": "#0a4f2c",
            "answer_border": "#53d769",
        }

        # --- Header with drag ---
        header = tk.Frame(self.root, bg=colors["header"], height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_label = tk.Label(
            header, text="SCREEN ANALYZER + AI", font=self.title_font,
            bg=colors["header"], fg=colors["accent"]
        )
        title_label.pack(side="left", padx=12, pady=6)

        # Drag bindings on header
        header.bind("<Button-1>", self._start_drag)
        header.bind("<B1-Motion>", self._do_drag)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        # --- Status bar ---
        self.status_frame = tk.Frame(self.root, bg=colors["bg"], height=25)
        self.status_frame.pack(fill="x")
        self.status_frame.pack_propagate(False)

        self.status_indicator = tk.Label(
            self.status_frame, text="ACTIVO", font=self.small_font,
            bg=colors["bg"], fg=colors["success"]
        )
        self.status_indicator.pack(side="left", padx=12)

        self.clarity_label = tk.Label(
            self.status_frame, text="", font=self.small_font,
            bg=colors["bg"], fg=colors["text_dim"]
        )
        self.clarity_label.pack(side="right", padx=12)

        # --- Scrollable content area ---
        canvas = tk.Canvas(self.root, bg=colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.content_frame = tk.Frame(canvas, bg=colors["bg"])

        self.content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.content_frame, anchor="nw", width=500)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        content = self.content_frame

        # --- Question section ---
        q_header = tk.Label(
            content, text="PREGUNTA DETECTADA", font=self.small_font,
            bg=colors["bg"], fg=colors["text_dim"], anchor="w"
        )
        q_header.pack(fill="x", pady=(5, 2))

        self.question_frame = tk.Frame(content, bg=colors["card"], bd=0,
                                        highlightthickness=1, highlightbackground="#2a2a4a")
        self.question_frame.pack(fill="x", pady=(0, 8))

        self.question_label = tk.Label(
            self.question_frame, text="Esperando captura...",
            font=self.body_font, bg=colors["card"], fg=colors["text"],
            wraplength=460, justify="left", anchor="w", padx=12, pady=10
        )
        self.question_label.pack(fill="x")

        # --- Options section ---
        self.opt_header = tk.Label(
            content, text="OPCIONES DETECTADAS", font=self.small_font,
            bg=colors["bg"], fg=colors["text_dim"], anchor="w"
        )
        self.opt_header.pack(fill="x", pady=(5, 2))

        self.options_frame = tk.Frame(content, bg=colors["bg"])
        self.options_frame.pack(fill="x", pady=(0, 8))

        self.options_labels = []
        for i in range(6):  # Max 6 options
            lbl = tk.Label(
                self.options_frame, text="", font=self.body_font,
                bg=colors["option_bg"], fg=colors["text"],
                anchor="w", padx=12, pady=4,
                highlightthickness=1, highlightbackground="#2a2a4a"
            )
            self.options_labels.append(lbl)

        # --- AI Answer section ---
        ans_header = tk.Label(
            content, text="RESPUESTA IA", font=self.small_font,
            bg=colors["bg"], fg=colors["success"], anchor="w"
        )
        ans_header.pack(fill="x", pady=(5, 2))

        self.answer_frame = tk.Frame(content, bg=colors["answer_bg"], bd=0,
                                      highlightthickness=2, highlightbackground=colors["answer_border"])
        self.answer_frame.pack(fill="x", pady=(0, 4))

        self.answer_label = tk.Label(
            self.answer_frame, text="Esperando pregunta...",
            font=self.answer_font, bg=colors["answer_bg"], fg="#ffffff",
            wraplength=450, justify="left", anchor="w", padx=12, pady=10
        )
        self.answer_label.pack(fill="x")

        # Explanation sub-label
        self.explanation_label = tk.Label(
            self.answer_frame, text="",
            font=self.body_font, bg=colors["answer_bg"], fg="#b0e0c0",
            wraplength=450, justify="left", anchor="w", padx=12, pady=0
        )
        self.explanation_label.pack(fill="x", pady=(0, 8))

        # --- Confidence section ---
        self.confidence_frame = tk.Frame(content, bg=colors["bg"], height=40)
        self.confidence_frame.pack(fill="x", pady=(4, 8))

        conf_left = tk.Frame(self.confidence_frame, bg=colors["bg"])
        conf_left.pack(fill="x", padx=12)

        self.confidence_label = tk.Label(
            conf_left, text="CONFIANZA: --",
            font=self.conf_font, bg=colors["bg"], fg=colors["text_dim"],
            anchor="w"
        )
        self.confidence_label.pack(side="left")

        self.pass_label = tk.Label(
            conf_left, text="",
            font=self.small_font, bg=colors["bg"], fg=colors["text_dim"],
            anchor="e"
        )
        self.pass_label.pack(side="right")

        # Visual confidence bar
        self.confidence_bar_bg = tk.Frame(
            self.confidence_frame, bg="#2a2a4a", height=14
        )
        self.confidence_bar_bg.pack(fill="x", padx=12, pady=(4, 0))

        self.confidence_bar_fill = tk.Frame(
            self.confidence_bar_bg, bg=colors["text_dim"], height=14, width=0
        )
        self.confidence_bar_fill.place(x=0, y=0, height=14, width=0)

        # --- Comment section ---
        self.comment_label = tk.Label(
            content, text="", font=self.status_font,
            bg=colors["bg"], fg=colors["text_dim"],
            wraplength=460, justify="left", anchor="w"
        )
        self.comment_label.pack(fill="x", pady=(5, 0))

        # --- Button bar ---
        btn_frame = tk.Frame(self.root, bg=colors["header"], height=40)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        btn_style = {
            "font": self.small_font,
            "bd": 0,
            "padx": 16,
            "pady": 4,
            "cursor": "hand2",
        }

        self.pause_btn = tk.Button(
            btn_frame, text="Pausar",
            bg=colors["warning"], fg="#1a1a2e",
            command=self._toggle_pause, **btn_style
        )
        self.pause_btn.pack(side="left", padx=8, pady=6)

        quit_btn = tk.Button(
            btn_frame, text="Salir",
            bg=colors["accent"], fg="white",
            command=self._quit, **btn_style
        )
        quit_btn.pack(side="right", padx=8, pady=6)

        self.colors = colors

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() - self._drag_data["x"] + event.x
        y = self.root.winfo_y() - self._drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="Reanudar", bg=self.colors["success"])
            self.status_indicator.config(text="PAUSADO", fg=self.colors["warning"])
            if self.on_pause_callback:
                self.on_pause_callback()
        else:
            self.pause_btn.config(text="Pausar", bg=self.colors["warning"])
            self.status_indicator.config(text="ACTIVO", fg=self.colors["success"])
            if self.on_resume_callback:
                self.on_resume_callback()

    def _quit(self):
        self.root.quit()
        self.root.destroy()

    def update_results(self, analysis: dict):
        """Update the overlay with new analysis results."""
        # Update question
        question = analysis.get("pregunta_detectada")
        if question:
            self.question_label.config(text=question, fg=self.colors["text"])
        else:
            self.question_label.config(text="No se detecto pregunta.", fg=self.colors["text_dim"])

        # Update options (handle both string and dict formats)
        options = analysis.get("opciones_detectadas", [])
        if options:
            self.opt_header.pack(fill="x", pady=(5, 2))
            self.options_frame.pack(fill="x", pady=(0, 8))
        else:
            self.opt_header.pack_forget()
            self.options_frame.pack_forget()

        for i, lbl in enumerate(self.options_labels):
            if i < len(options):
                opt = options[i]
                text = opt["text"] if isinstance(opt, dict) else opt
                lbl.config(text=text)
                lbl.pack(fill="x", pady=1)
            else:
                lbl.pack_forget()

        # Update clarity
        clarity = analysis.get("claridad", "no_detectada")
        clarity_colors = {
            "clara": (self.colors["success"], "Clara"),
            "ambigua": (self.colors["warning"], "Ambigua"),
            "no_detectada": (self.colors["accent"], "No detectada"),
        }
        color, text = clarity_colors.get(clarity, (self.colors["text_dim"], clarity))
        self.clarity_label.config(text=text, fg=color)

        # Update comment
        comment = analysis.get("comentario", "")
        self.comment_label.config(text=comment)

    def update_confidence(self, confidence: int):
        """Update the confidence display with color-coding and visual bar."""
        if confidence >= 90:
            color = self.colors["success"]
            label = "ALTA"
        elif confidence >= 70:
            color = self.colors["warning"]
            label = "MEDIA"
        else:
            color = self.colors["accent"]
            label = "BAJA"

        self.confidence_label.config(
            text=f"CONFIANZA: {confidence}% ({label})",
            fg=color
        )

        # Update bar (use parent width or default 480)
        try:
            bar_max = self.confidence_bar_bg.winfo_width()
            if bar_max < 50:
                bar_max = 480
        except Exception:
            bar_max = 480
        bar_width = int(confidence * bar_max / 100)
        self.confidence_bar_fill.place(x=0, y=0, height=14, width=bar_width)
        self.confidence_bar_fill.config(bg=color)

    def update_answer(self, ai_result: dict):
        """Update the AI answer section with answer, explanation, and confidence."""
        if not ai_result:
            return

        error = ai_result.get("error")
        if error:
            self.answer_label.config(text=f"Error: {error}", fg=self.colors["accent"])
            self.explanation_label.config(text="")
            self.update_confidence(0)
            return

        respuesta = ai_result.get("respuesta", "Sin respuesta")
        explicacion = ai_result.get("explicacion", "")
        confianza = ai_result.get("confianza", 0)
        pass_count = ai_result.get("pass_count", 1)

        self.answer_label.config(text=f"{respuesta}", fg="#ffffff")

        if explicacion:
            # Truncate long explanations for UI
            if len(explicacion) > 300:
                explicacion = explicacion[:300] + "..."
            self.explanation_label.config(text=explicacion)
        else:
            self.explanation_label.config(text="")

        # Update confidence display
        self.update_confidence(confianza)

        # Show pass count
        if pass_count and pass_count > 1:
            self.pass_label.config(
                text=f"Verificado ({pass_count} pasadas)",
                fg=self.colors["success"]
            )
        else:
            self.pass_label.config(
                text="1 pasada",
                fg=self.colors["text_dim"]
            )

    def set_answer_loading(self):
        """Show loading state in answer section."""
        self.answer_label.config(text="Consultando IA...", fg=self.colors["warning"])
        self.explanation_label.config(text="")
        self.confidence_label.config(text="CONFIANZA: --", fg=self.colors["text_dim"])
        self.confidence_bar_fill.place(x=0, y=0, height=14, width=0)
        self.pass_label.config(text="")

    def schedule(self, ms: int, callback):
        """Schedule a callback on the tkinter main loop."""
        self.root.after(ms, callback)

    def run(self):
        """Start the tkinter main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    overlay = OverlayWindow()

    def test_update():
        overlay.update_results({
            "pregunta_detectada": "Cual es la capital de Francia?",
            "opciones_detectadas": ["a) Madrid", "b) Paris", "c) Roma", "d) Berlin"],
            "claridad": "clara",
            "comentario": "Lineas procesadas: 4 | Ruido filtrado: 6"
        })
        overlay.update_answer({
            "respuesta": "b) Paris",
            "explicacion": "Paris es la capital de Francia desde hace siglos.",
            "confianza": 98,
            "pass_count": 2,
            "error": None
        })

    overlay.schedule(1000, test_update)
    overlay.run()
