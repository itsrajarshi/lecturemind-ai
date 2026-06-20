import json
import re

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL
from utils.prompts import FLASHCARDS_PROMPT, NOTES_PROMPT, QUIZ_PROMPT


def _client() -> Groq:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Add it to backend/.env")
    return Groq(api_key=GROQ_API_KEY)


def _chat(prompt: str, temperature: float = 0.3) -> str:
    client = _client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are LectureMind AI, an academic assistant. Follow instructions precisely.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def generate_notes(transcript: str) -> str:
    prompt = NOTES_PROMPT.format(transcript=transcript[:12000])
    return _chat(prompt, temperature=0.2)


def generate_quiz(transcript: str) -> dict:
    prompt = QUIZ_PROMPT.format(transcript=transcript[:12000])
    raw = _chat(prompt, temperature=0.4)
    data = _parse_json(raw)
    if len(data.get("questions", [])) != 10:
        raise ValueError("Quiz must contain exactly 10 questions")
    return data


def generate_flashcards(transcript: str) -> dict:
    prompt = FLASHCARDS_PROMPT.format(transcript=transcript[:12000])
    raw = _chat(prompt, temperature=0.35)
    return _parse_json(raw)
