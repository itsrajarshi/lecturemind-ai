import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", BASE_DIR / "uploads"))
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}

# ---- Limits ----
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", 6 * 60 * 60))
SESSION_CLEANUP_INTERVAL = int(os.getenv("SESSION_CLEANUP_INTERVAL", 300))

# ---- Rate limiting (per IP, per window) ----
RATE_LIMIT_TRANSCRIBE = int(os.getenv("RATE_LIMIT_TRANSCRIBE", 5))
RATE_LIMIT_GENERATE = int(os.getenv("RATE_LIMIT_GENERATE", 20))
RATE_LIMIT_WINDOW = 3600

# ---- Groq / AI ----
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_TIMEOUT = float(os.getenv("GROQ_TIMEOUT", 90))
GROQ_MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", 1))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3")
WHISPER_TIMEOUT = float(os.getenv("WHISPER_TIMEOUT", 120))
TRANSCRIPT_MAX_CHARS = int(os.getenv("TRANSCRIPT_MAX_CHARS", 40_000))

# ---- Security ----
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# True when running on Render (or any production host)
IS_PRODUCTION = os.getenv("RENDER", "").lower() in {"true", "1", "yes"} or os.getenv(
    "FLASK_ENV", ""
).lower() == "production"


def validate_config() -> None:
    """Fail fast in production if required secrets are missing."""
    if IS_PRODUCTION and not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it in the Render dashboard (or the "
            "host environment) before deploying."
        )