"""Unit tests for utils.parsing (LLM structured-output extraction + validation)."""

import pytest

from utils.parsing import (
    SchemaError,
    extract_json_object,
    validate_flashcards,
    validate_quiz,
)


class TestExtractJsonObject:
    def test_plain_json(self):
        assert extract_json_object('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        raw = 'Here you go:\n```json\n{"a": 1}\n```\nThanks!'
        assert extract_json_object(raw) == {"a": 1}

    def test_fence_without_language(self):
        raw = '```\n{"a": 1}\n```'
        assert extract_json_object(raw) == {"a": 1}

    def test_object_embedded_in_prose(self):
        raw = 'The result was {"quiz_title": "T", "questions": []} end.'
        assert extract_json_object(raw) == {"quiz_title": "T", "questions": []}

    def test_skips_leading_bad_region(self):
        raw = 'prefix {bad json} then {"a": 1}'
        assert extract_json_object(raw) == {"a": 1}

    def test_nested_braces_and_escaped_quotes(self):
        raw = '{"a": {"b": "say \\"hi\\""}, "c": [1, 2]}'
        assert extract_json_object(raw) == {"a": {"b": 'say "hi"'}, "c": [1, 2]}

    def test_empty_input_raises(self):
        with pytest.raises(SchemaError):
            extract_json_object("   ")

    def test_array_input_raises(self):
        with pytest.raises(SchemaError):
            extract_json_object("[1, 2, 3]")

    def test_garbage_raises(self):
        with pytest.raises(SchemaError):
            extract_json_object("this is not json at all")


def _quiz(questions=None, title="Quiz"):
    return {"quiz_title": title, "questions": questions or []}


def _question(index=1, overrides=None):
    base = {
        "id": index,
        "question": f"Question {index}?",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_answer": "A",
        "difficulty": "easy",
        "explanation": "Because.",
    }
    base.update(overrides or {})
    return base


class TestValidateQuiz:
    def test_valid_quiz(self):
        data = _quiz([_question(i) for i in range(1, 11)])
        result = validate_quiz(data)
        assert len(result["questions"]) == 10
        assert result["quiz_title"] == "Quiz"

    def test_rejects_wrong_question_count(self):
        with pytest.raises(SchemaError):
            validate_quiz(_quiz([_question(i) for i in range(1, 10)]))

    def test_rejects_missing_options(self):
        with pytest.raises(SchemaError):
            validate_quiz(_quiz([_question(1, {"options": {"A": "1", "B": "2"}})]))

    def test_rejects_bad_correct_answer(self):
        with pytest.raises(SchemaError):
            validate_quiz(_quiz([_question(1, {"correct_answer": "E"})]))

    def test_normalizes_difficulty(self):
        data = _quiz([_question(i, {"difficulty": "impossible"}) for i in range(1, 11)])
        assert all(q["difficulty"] == "medium" for q in validate_quiz(data)["questions"])

    def test_rejects_duplicate_questions(self):
        q = _question(1)
        with pytest.raises(SchemaError):
            validate_quiz(_quiz([q, {**q, "id": 2}]))


class TestValidateFlashcards:
    def test_valid_deck(self):
        cards = [{"id": i, "question": f"Q{i}", "answer": f"A{i}"} for i in range(1, 6)]
        result = validate_flashcards({"deck_title": "D", "flashcards": cards})
        assert len(result["flashcards"]) == 5

    def test_caps_at_15_and_dedupes(self):
        cards = [
            {"id": i, "question": f"Q{i}", "answer": "A"}
            for i in range(1, 20)
        ]
        cards.append({"id": 99, "question": "Q1", "answer": "dup"})
        result = validate_flashcards({"flashcards": cards})
        assert len(result["flashcards"]) == 15

    def test_rejects_empty_deck(self):
        with pytest.raises(SchemaError):
            validate_flashcards({"flashcards": []})

    def test_rejects_too_small_deck(self):
        with pytest.raises(SchemaError):
            validate_flashcards({"flashcards": [{"question": "Q", "answer": "A"}]})