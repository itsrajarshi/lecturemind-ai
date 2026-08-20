import logging

from groq import Groq

from config import GROQ_API_KEY, WHISPER_MODEL, WHISPER_TIMEOUT
from utils.logging import get_logger

logger = get_logger("lecturemind.whisper")

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured")
        _client = Groq(api_key=GROQ_API_KEY, timeout=WHISPER_TIMEOUT)
    return _client


def _as_text(value) -> str:
    return str(value or "").strip()


def _as_float(value) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _segment_text(seg) -> str:
    if isinstance(seg, dict):
        return _as_text(seg.get("text"))
    return _as_text(getattr(seg, "text", ""))


def _segment_time(seg, field: str) -> float:
    if isinstance(seg, dict):
        return _as_float(seg.get(field))
    return _as_float(getattr(seg, field, 0))


def transcribe_audio(file_path: str) -> dict:
    """Transcribe an audio file via the Groq-hosted Whisper API.

    Uses `verbose_json` so segment timestamps and the detected language come
    back alongside the plain text. The SDK models only the `text` field; the
    remaining fields are read defensively via attribute/dict access so this
    keeps working across SDK versions.
    """
    client = get_client()

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=WHISPER_MODEL,
            response_format="verbose_json",
        )

    text = _as_text(getattr(transcription, "text", ""))
    language = _as_text(getattr(transcription, "language", "")) or "unknown"

    segments = []
    raw_segments = getattr(transcription, "segments", None) or []
    for seg in raw_segments:
        seg_text = _segment_text(seg)
        if not seg_text:
            continue
        segments.append(
            {
                "start": _segment_time(seg, "start"),
                "end": _segment_time(seg, "end"),
                "text": seg_text,
            }
        )

    logger.info(
        "transcription_completed model=%s text_chars=%d segments=%d language=%s",
        WHISPER_MODEL,
        len(text),
        len(segments),
        language,
    )
    return {"text": text, "language": language, "segments": segments}