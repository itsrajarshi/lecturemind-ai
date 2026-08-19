"""Tests for POST /api/download/notes.

PDF export must survive realistic LLM output: multi-line markdown, bullet
characters, Hindi/Devanagari text, and long unbroken tokens.
"""

TXT_NOTES = "# Lecture Notes\n\n- Point one\n- Point two"
PDF_NOTES = "# Machine Learning\n\n## Supervised Learning\n\n- **Definition**: Learning from labeled data\n- Hindi: हिंदी में नोट्स\n- Long unbroken token: " + "A" * 200 + "\n\n## Key Takeaways\n\n1. First point\n2. Second point"


def test_download_notes_txt(app):
    resp = app.post(
        "/api/download/notes",
        json={"notes": TXT_NOTES, "title": "My Notes", "format": "txt"},
    )
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/plain")
    body = resp.get_data(as_text=True)
    assert "My Notes" in body
    assert "- Point one" in body
    assert "- Point two" in body


def test_download_notes_pdf(app):
    resp = app.post(
        "/api/download/notes",
        json={"notes": PDF_NOTES, "title": "My Notes", "format": "pdf"},
    )
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/pdf")
    assert resp.get_data().startswith(b"%PDF")


def test_download_notes_pdf_multiline_and_unicode(app):
    """Regression: multi-line bullets + Devanagari + long tokens must not 500."""
    resp = app.post(
        "/api/download/notes",
        json={"notes": PDF_NOTES, "title": "My Notes", "format": "pdf"},
    )
    assert resp.status_code == 200
    assert resp.get_data().startswith(b"%PDF")


def test_download_notes_invalid_format(app):
    resp = app.post(
        "/api/download/notes",
        json={"notes": PDF_NOTES, "format": "docx"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_download_notes_missing_notes(app):
    resp = app.post("/api/download/notes", json={"format": "txt"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()