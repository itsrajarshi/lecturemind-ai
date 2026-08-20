"""Export study notes as plain text or PDF.

PDF generation bundles two Unicode fonts so that both Latin and Devanagari
(Hindi) lecture notes render correctly:

* DejaVu Sans (primary) — broad Latin/Greek/Cyrillic coverage
* Noto Sans Devanagari (fallback) — Hindi/Sanskrit coverage

Markdown syntax is stripped and long words are wrapped so `multi_cell` never
hits fpdf2's "not enough horizontal space" crash. Any character still not
covered by the bundled fonts is replaced so export can never fail on content.
"""

import re
import textwrap
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from fpdf.errors import FPDFException

from config import BASE_DIR
from utils.logging import get_logger
from utils.security import AppError

logger = get_logger("lecturemind.export")

MAX_TITLE_LENGTH = 120
MAX_NOTES_LENGTH = 1_000_000
LINE_WIDTH = 72

FONT_DIR = BASE_DIR / "assets" / "fonts"
FONT_DEJAVU = FONT_DIR / "DejaVuSans.ttf"
FONT_DEVANAGARI = FONT_DIR / "NotoSansDevanagari-Regular.ttf"


def _validate(notes: str, title: str) -> str:
    if not notes or not notes.strip():
        raise AppError("Notes content required", status=400)
    if len(notes) > MAX_NOTES_LENGTH:
        raise AppError("Notes content is too large to export", status=413)
    return (title or "Lecture Notes")[:MAX_TITLE_LENGTH]


def _sanitize_markdown(line: str) -> str:
    """Strip common markdown syntax so plain-text output stays readable."""
    text = line.strip()
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "• ", text)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return text.strip()


def _pdf_lines(notes: str) -> list[str]:
    """Convert markdown notes into wrapped, PDF-safe plain-text lines."""
    lines: list[str] = []
    for raw in notes.split("\n"):
        text = _sanitize_markdown(raw)
        if not text:
            lines.append("")
            continue
        bullet = ""
        if text.startswith("• "):
            bullet, text = "• ", text[2:]
        wrapped = (
            textwrap.wrap(text, width=LINE_WIDTH, break_long_words=True, break_on_hyphens=False)
            or [""]
        )
        lines.append(bullet + wrapped[0])
        for rest in wrapped[1:]:
            lines.append("  " + rest)
    return lines


def _add_fonts(pdf: FPDF) -> bool:
    """Register bundled Unicode fonts. Returns True if fonts were registered."""
    if not (FONT_DEJAVU.is_file() and FONT_DEVANAGARI.is_file()):
        return False
    pdf.add_font("DejaVu", "", str(FONT_DEJAVU))
    pdf.add_font("NotoDevanagari", "", str(FONT_DEVANAGARI))
    try:
        pdf.set_fallback_fonts(["NotoDevanagari"])
    except Exception:
        # Fallback registration is best-effort; primary font still works.
        pass
    return True


def _safe_multi_cell(pdf: FPDF, line: str) -> None:
    """Render a line, degrading gracefully if a glyph is missing from all fonts.

    Only fpdf's own rendering failures are caught (primarily missing glyphs).
    Any other exception is a real bug and propagates to the route's error
    handler so it is logged and surfaced, rather than silently swallowed.
    """
    try:
        pdf.multi_cell(0, 5.5, line)
    except FPDFException:
        logger.warning("pdf_glyph_fallback line_chars=%d preview=%r", len(line), line[:40])
        safe = line.encode("ascii", "replace").decode("ascii")
        try:
            pdf.multi_cell(0, 5.5, safe)
        except FPDFException:
            logger.warning("pdf_line_skipped line_chars=%d", len(line))


def notes_to_txt(notes: str, title: str = "Lecture Notes") -> bytes:
    title = _validate(notes, title)
    content = f"{title}\n{'=' * len(title)}\n\n{notes}"
    return content.encode("utf-8")


def notes_to_pdf(notes: str, title: str = "Lecture Notes") -> bytes:
    title = _validate(notes, title)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if _add_fonts(pdf):
        font_name = "DejaVu"
        pdf.set_font(font_name, size=16)
        pdf.multi_cell(0, 10, title)
        pdf.ln(4)
        pdf.set_font(font_name, size=10)
    else:
        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 10, title)
        pdf.ln(4)
        pdf.set_font("Helvetica", size=10)

    for line in _pdf_lines(notes):
        if not line.strip():
            pdf.ln(3)
            continue
        _safe_multi_cell(pdf, line)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()