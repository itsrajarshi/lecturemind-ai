from io import BytesIO

from fpdf import FPDF

from utils.security import AppError

MAX_TITLE_LENGTH = 120
MAX_NOTES_LENGTH = 1_000_000


def _validate(notes: str, title: str) -> None:
    if not notes or not notes.strip():
        raise AppError("Notes content required", status=400)
    if len(notes) > MAX_NOTES_LENGTH:
        raise AppError("Notes content is too large to export", status=413)
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH]
    return title or "Lecture Notes"


def notes_to_txt(notes: str, title: str = "Lecture Notes") -> bytes:
    title = _validate(notes, title)
    content = f"{title}\n{'=' * len(title)}\n\n{notes}"
    return content.encode("utf-8")


def notes_to_pdf(notes: str, title: str = "Lecture Notes") -> bytes:
    title = _validate(notes, title)
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