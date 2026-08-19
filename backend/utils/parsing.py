"""Robust extraction and validation of structured output from LLMs.

LLMs occasionally wrap JSON in markdown fences, prepend prose, or return
slightly malformed data. These helpers normalize the output and validate it
against the shapes LectureMind depends on before it reaches the frontend.
"""

import json
import re
from typing import Any, Dict

from utils.logging import get_logger

logger = get_logger("lecturemind.parsing")


class SchemaError(ValueError):
    """Raised when model output does not conform to the expected schema."""


def extract_json_object(raw: str) -> Dict[str, Any]:
    """Extract a JSON object from a model response.

    Handles: fenced code blocks, trailing prose, and embedded JSON objects.
    """
    if not raw or not raw.strip():
        raise SchemaError("Empty model response")

    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if in_str:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_str = False
                continue
            if char == '"':
                in_str = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start : i + 1])
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break

    raise SchemaError("Could not parse JSON from model output")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def validate_quiz(data: Any) -> Dict[str, Any]:
    """Validate and normalize a quiz object (exactly 10 questions)."""
    if not isinstance(data, dict):
        raise SchemaError("Quiz response must be a JSON object")

    questions = data.get("questions")
    if not isinstance(questions, list):
        raise SchemaError("Quiz response is missing a questions list")
    if len(questions) != 10:
        raise SchemaError(f"Quiz must contain exactly 10 questions (got {len(questions)})")

    result: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, q in enumerate(questions):
        if not isinstance(q, dict):
            raise SchemaError(f"Question {index + 1} is not an object")

        question = _clean(q.get("question"))
        options = q.get("options")
        correct = q.get("correct_answer")
        difficulty = _clean(q.get("difficulty")).lower()
        explanation = _clean(q.get("explanation"))

        if not question:
            raise SchemaError(f"Question {index + 1} is missing text")

        if not isinstance(options, dict):
            raise SchemaError(f"Question {index + 1} is missing options")

        letters = [k for k in ("A", "B", "C", "D") if k in options and _clean(options[k])]
        if len(letters) != 4:
            raise SchemaError(
                f"Question {index + 1} must have exactly 4 options A-D (got {len(letters)})"
            )
        if correct not in letters:
            raise SchemaError(f"Question {index + 1} correct_answer must be one of {letters}")

        key = question.casefold()
        if key in seen:
            raise SchemaError(f"Duplicate question: {question[:60]}...")
        seen.add(key)

        result.append(
            {
                "id": index + 1,
                "question": question,
                "options": {k: _clean(options[k]) for k in letters},
                "correct_answer": correct,
                "difficulty": difficulty if difficulty in ("easy", "medium", "hard") else "medium",
                "explanation": explanation,
            }
        )

    return {"quiz_title": _clean(data.get("quiz_title")) or "Practice Quiz", "questions": result}


def validate_flashcards(data: Any) -> Dict[str, Any]:
    """Validate and normalize a flashcard deck (5-15 cards, de-duplicated)."""
    if not isinstance(data, dict):
        raise SchemaError("Flashcard response must be a JSON object")

    cards = data.get("flashcards")
    if not isinstance(cards, list) or not cards:
        raise SchemaError("Flashcard response is missing a flashcards list")

    result: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            continue
        question = _clean(card.get("question"))
        answer = _clean(card.get("answer"))
        if not question or not answer:
            continue
        key = question.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append({"id": len(result) + 1, "question": question, "answer": answer})
        if len(result) >= 15:
            break

    if len(result) < 5:
        raise SchemaError(f"Flashcard deck too small (got {len(result)} valid cards)")

    return {"deck_title": _clean(data.get("deck_title")) or "Revision Deck", "flashcards": result}