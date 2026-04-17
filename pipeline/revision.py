"""Revision Stage: classify feedback dan route ke specialist yang tepat."""
from pipeline.models import RevisionInput


CSS_KEYWORDS = ["warna", "font", "ukuran", "animasi", "background", "gradient", "shadow",
                "border", "margin", "padding", "opacity", "transisi", "hover", "theme", "gelap", "terang"]

HTML_KEYWORDS = ["layout", "teks", "tombol", "gambar", "posisi", "struktur", "elemen",
                 "tampilan", "judul", "header", "footer", "form", "input"]

COMPLEX_KEYWORDS = ["soal", "jawaban", "skor", "mekanik", "level", "timer", "logika",
                    "bug", "error", "salah", "gameplay", "kondisi", "menang", "kalah",
                    "pertanyaan", "challenge", "stage"]


def classify(feedback: str) -> RevisionInput:
    """Klasifikasi feedback guru: css, html, atau complex."""
    lower = feedback.lower()

    css_score = sum(1 for kw in CSS_KEYWORDS if kw in lower)
    html_score = sum(1 for kw in HTML_KEYWORDS if kw in lower)
    complex_score = sum(1 for kw in COMPLEX_KEYWORDS if kw in lower)

    if complex_score > css_score and complex_score > html_score:
        return RevisionInput(feedback=feedback, category="complex")
    elif css_score >= html_score:
        return RevisionInput(feedback=feedback, category="css")
    else:
        return RevisionInput(feedback=feedback, category="html")
