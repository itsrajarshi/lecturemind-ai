from io import BytesIO
from pathlib import Path

from fpdf import FPDF


def notes_to_txt(notes: str, title: str = "Lecture Notes") -> bytes:
    content = f"{title}\n{'=' * len(title)}\n\n{notes}"
    return content.encode("utf-8")


def notes_to_pdf(notes: str, title: str = "Lecture Notes") -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)

    for line in notes.split("\n"):
        clean = (
            line.replace("**", "")
            .replace("### ", "")
            .replace("## ", "")
            .replace("# ", "")
            .strip()
        )
        if not clean:
            pdf.ln(3)
            continue
        if clean.startswith("- "):
            clean = "  • " + clean[2:]
        pdf.multi_cell(0, 6, clean)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
