"""Tests for POST /api/generate/{notes,quiz,flashcards}."""

import app as app_module
from services.groq_service import GenerationError
from services.session_store import store

NOTES_MD = "# Notes\n\nSome **markdown** generated notes."
QUIZ = {
    "title": "Quiz",
    "questions": [{"question": "Q1?", "options": ["a", "b"], "answer": 0}],
}
CARDS = {"flashcards": [{"front": "Term", "back": "Definition"}]}
TRANSCRIPT = "This is the lecture transcript used for generation."


def _create_session():
    return store.create(
        transcript=TRANSCRIPT,
        segments=[{"start": 0.0, "end": 1.0, "text": TRANSCRIPT}],
        language="en",
        filepath="",
    )


def test_notes_success(app, monkeypatch):
    monkeypatch.setattr(app_module, "generate_notes", lambda transcript: NOTES_MD)
    resp = app.post("/api/generate/notes", json={"transcript": TRANSCRIPT})
    assert resp.status_code == 200
    assert resp.get_json() == {"notes": NOTES_MD, "format": "markdown"}


def test_quiz_success_with_session_header(app, monkeypatch):
    session_id = _create_session()
    monkeypatch.setattr(app_module, "generate_quiz", lambda transcript: QUIZ)
    resp = app.post(
        "/api/generate/quiz",
        headers={"X-Session-Id": session_id},
        json={},
    )
    assert resp.status_code == 200
    assert resp.get_json() == QUIZ
    # The transcript is resolved from the session, and the session survives.
    assert store.get(session_id)["transcript"] == TRANSCRIPT


def test_flashcards_success_with_session_header(app, monkeypatch):
    session_id = _create_session()
    monkeypatch.setattr(app_module, "generate_flashcards", lambda transcript: CARDS)
    resp = app.post(
        "/api/generate/flashcards",
        headers={"X-Session-Id": session_id},
        json={},
    )
    assert resp.status_code == 200
    assert resp.get_json() == CARDS
    assert store.get(session_id)["transcript"] == TRANSCRIPT


def test_quiz_success_with_body_transcript(app, monkeypatch):
    monkeypatch.setattr(app_module, "generate_quiz", lambda transcript: QUIZ)
    resp = app.post("/api/generate/quiz", json={"transcript": TRANSCRIPT})
    assert resp.status_code == 200
    assert resp.get_json() == QUIZ


def test_generate_empty_body_returns_400(app):
    resp = app.post("/api/generate/notes", json={})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Transcript required"}


def test_generation_error_returns_502(app, monkeypatch):
    def _boom(transcript):
        raise GenerationError("x")

    monkeypatch.setattr(app_module, "generate_notes", _boom)
    resp = app.post("/api/generate/notes", json={"transcript": TRANSCRIPT})
    assert resp.status_code == 502
    assert resp.get_json() == {"error": "x"}


def test_generation_generic_error_is_sanitized(app, monkeypatch):
    def _boom(transcript):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(app_module, "generate_notes", _boom)
    resp = app.post("/api/generate/notes", json={"transcript": TRANSCRIPT})
    assert resp.status_code == 500
    body_text = resp.get_data(as_text=True)
    assert "secret" not in body_text
    assert resp.get_json() == {"error": "Something went wrong. Please try again."}
