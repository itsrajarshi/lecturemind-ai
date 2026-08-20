"""Tests for the LLM retry/fallback path and transcript truncation.

These exercise `generate_quiz`/`generate_flashcards` with a mocked `_chat` that
returns invalid then valid JSON, and `generate_notes` for empty output.
"""

import pytest

import services.groq_service as groq_service
from services.groq_service import GenerationError, _truncate, generate_flashcards, generate_quiz

VALID_QUIZ = {
    "quiz_title": "Quiz",
    "questions": [
        {
            "id": i,
            "question": f"Q{i}?",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "A",
            "difficulty": "easy",
            "explanation": "x",
        }
        for i in range(1, 11)
    ],
}

VALID_CARDS = {
    "deck_title": "D",
    "flashcards": [{"id": i, "question": f"Q{i}", "answer": "A"} for i in range(1, 6)],
}

TRANSCRIPT = "A lecture transcript about machine learning concepts and examples."


def test_generate_quiz_retries_on_invalid_then_valid(monkeypatch):
    calls = []

    def fake_chat(prompt, temperature=0.3, max_tokens=4096, deadline=None):
        calls.append(1)
        if len(calls) == 1:
            return "not json at all"
        return (
            "```json\n"
            + __import__("json").dumps(VALID_QUIZ)
            + "\n```"
        )

    monkeypatch.setattr(groq_service, "_chat", fake_chat)
    result = generate_quiz(TRANSCRIPT)
    assert result["quiz_title"] == "Quiz"
    assert len(result["questions"]) == 10
    assert len(calls) == 2


def test_generate_flashcards_retries_on_invalid_then_valid(monkeypatch):
    calls = []

    def fake_chat(prompt, temperature=0.3, max_tokens=4096, deadline=None):
        calls.append(1)
        if len(calls) == 1:
            return '{"flashcards": []}'  # too small -> SchemaError
        return __import__("json").dumps(VALID_CARDS)

    monkeypatch.setattr(groq_service, "_chat", fake_chat)
    result = generate_flashcards(TRANSCRIPT)
    assert result["deck_title"] == "D"
    assert len(result["flashcards"]) == 5
    assert len(calls) == 2


def test_generate_quiz_raises_after_two_invalid_attempts(monkeypatch):
    monkeypatch.setattr(groq_service, "_chat", lambda *a, **k: "still not json")
    with pytest.raises(GenerationError):
        generate_quiz(TRANSCRIPT)


def test_generate_flashcards_raises_after_two_invalid_attempts(monkeypatch):
    monkeypatch.setattr(groq_service, "_chat", lambda *a, **k: "nope")
    with pytest.raises(GenerationError):
        generate_flashcards(TRANSCRIPT)


def test_generate_notes_rejects_empty_output(monkeypatch):
    monkeypatch.setattr(groq_service, "_chat", lambda *a, **k: "  ")
    with pytest.raises(GenerationError):
        groq_service.generate_notes(TRANSCRIPT)


class TestTruncate:
    def test_short_transcript_unchanged(self):
        assert _truncate("short") == "short"

    def test_long_transcript_truncates_at_sentence_boundary(self):
        text = ("word " * 50) + ". " + ("word " * 1000)
        out = _truncate(text, limit=300)
        assert len(out) <= 320
        assert "truncated" in out
        assert out.endswith("]")

    def test_long_transcript_without_boundary(self):
        text = "A" * 1000
        out = _truncate(text, limit=100)
        assert out.startswith("A" * 100)
        assert "truncated" in out