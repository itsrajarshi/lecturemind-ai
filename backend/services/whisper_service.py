from groq import Groq

from config import GROQ_API_KEY

_client = None


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def transcribe_audio(file_path: str) -> dict:
    client = get_client()

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="verbose_json",
        )

    segments = []

    if hasattr(transcription, "segments") and transcription.segments:
        for seg in transcription.segments:
            segments.append(
            {
                "start": round(seg.get("start", 0), 2),
                "end": round(seg.get("end", 0), 2),
                "text": seg.get("text", "").strip(),
            }
        )
    return {
        "text": transcription.text.strip(),
        "language": getattr(transcription, "language", "unknown"),
        "segments": segments,
    }
    