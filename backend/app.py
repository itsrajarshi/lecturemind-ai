import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from io import BytesIO
from werkzeug.exceptions import RequestEntityTooLarge

from config import (
    BASE_DIR,
    CORS_ORIGINS,
    IS_PRODUCTION,
    MAX_CONTENT_LENGTH,
    RATE_LIMIT_GENERATE,
    RATE_LIMIT_TRANSCRIBE,
    RATE_LIMIT_WINDOW,
    UPLOAD_FOLDER,
    validate_config,
)
from services.export_service import notes_to_pdf, notes_to_txt
from services.groq_service import GenerationError, generate_flashcards, generate_notes, generate_quiz
from services.session_store import store
from services.whisper_service import transcribe_audio
from utils.file_validator import allowed_file, has_valid_signature, safe_filename
from utils.logging import configure_logging, get_logger
from utils.security import AppError, error_response, rate_limit

configure_logging()
logger = get_logger("lecturemind.app")

validate_config()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

_cors_origins = (
    [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
    if CORS_ORIGINS != "*"
    else "*"
)
CORS(app, resources={r"/api/*": {"origins": _cors_origins}})

STATIC_FOLDER = BASE_DIR / "static"


# --------------------------------------------------------------------------
# Request logging
# --------------------------------------------------------------------------

@app.before_request
def _before_request():
    request.environ["_start_time"] = time.perf_counter()
    store.maybe_sweep()


@app.after_request
def _after_request(response):
    start = request.environ.get("_start_time")
    duration_ms = (time.perf_counter() - start) * 1000 if start else 0
    if not request.path.startswith("/static"):
        logger.info(
            "http_request method=%s path=%s status=%d duration_ms=%.1f ip=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request.remote_addr,
        )
    if request.path.startswith("/api/"):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'",
        )
    return response


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _session_id_from_request() -> str:
    header = request.headers.get("X-Session-Id", "")
    if header:
        return header
    data = request.get_json(silent=True) or {}
    return data.get("session_id", "")


def _transcript_from(session_id: str, provided: str) -> str:
    """Resolve the transcript from the session, falling back to the body."""
    if session_id:
        session = store.get(session_id)
        if session:
            return session["transcript"]
    return (provided or "").strip()


def _handle_app_error(exc: AppError):
    return jsonify({"error": exc.message}), exc.status


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "LectureMind AI"})


@app.route("/api/transcribe", methods=["POST"])
@rate_limit(RATE_LIMIT_TRANSCRIBE, RATE_LIMIT_WINDOW, "transcribe")
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["audio"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file. Allowed: MP3, WAV, M4A"}), 400

    session_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = safe_filename(f"{session_id}.{ext}")
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    if not has_valid_signature(filepath):
        filepath.unlink(missing_ok=True)
        return jsonify(
            {"error": "The file does not appear to be valid audio. Allowed: MP3, WAV, M4A"}
        ), 400

    try:
        result = transcribe_audio(str(filepath))
    except Exception as exc:
        logger.exception("transcription_failed session_id=%s", session_id)
        try:
            filepath.unlink(missing_ok=True)
        except OSError:
            pass
        return error_response(exc)

    if not result["text"]:
        logger.warning("transcription_empty session_id=%s", session_id)
        filepath.unlink(missing_ok=True)
        return jsonify({"error": "No speech detected in the audio. Please try a clearer recording."}), 422

    new_session_id = store.create(
        transcript=result["text"],
        segments=result["segments"],
        language=result["language"],
        filepath=str(filepath),
    )

    return jsonify(
        {
            "session_id": new_session_id,
            "transcript": result["text"],
            "language": result["language"],
            "segments": result["segments"],
        }
    )


@app.route("/api/generate/notes", methods=["POST"])
@rate_limit(RATE_LIMIT_GENERATE, RATE_LIMIT_WINDOW, "generate")
def notes():
    data = request.get_json(silent=True) or {}
    session_id = _session_id_from_request()
    transcript = _transcript_from(session_id, data.get("transcript", ""))

    if not transcript:
        return jsonify({"error": "Transcript required"}), 400

    try:
        notes_md = generate_notes(transcript)
    except GenerationError as exc:
        logger.exception("notes_generation_failed session_id=%s", session_id)
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("notes_generation_failed session_id=%s", session_id)
        return error_response(exc)

    if session_id:
        store.update(session_id, notes=notes_md)

    return jsonify({"notes": notes_md, "format": "markdown"})


@app.route("/api/generate/quiz", methods=["POST"])
@rate_limit(RATE_LIMIT_GENERATE, RATE_LIMIT_WINDOW, "generate")
def quiz():
    data = request.get_json(silent=True) or {}
    session_id = _session_id_from_request()
    transcript = _transcript_from(session_id, data.get("transcript", ""))

    if not transcript:
        return jsonify({"error": "Transcript required"}), 400

    try:
        quiz_data = generate_quiz(transcript)
    except GenerationError as exc:
        logger.exception("quiz_generation_failed session_id=%s", session_id)
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("quiz_generation_failed session_id=%s", session_id)
        return error_response(exc)

    if session_id:
        store.update(session_id, quiz=quiz_data)

    return jsonify(quiz_data)


@app.route("/api/generate/flashcards", methods=["POST"])
@rate_limit(RATE_LIMIT_GENERATE, RATE_LIMIT_WINDOW, "generate")
def flashcards():
    data = request.get_json(silent=True) or {}
    session_id = _session_id_from_request()
    transcript = _transcript_from(session_id, data.get("transcript", ""))

    if not transcript:
        return jsonify({"error": "Transcript required"}), 400

    try:
        cards = generate_flashcards(transcript)
    except GenerationError as exc:
        logger.exception("flashcards_generation_failed session_id=%s", session_id)
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("flashcards_generation_failed session_id=%s", session_id)
        return error_response(exc)

    if session_id:
        store.update(session_id, flashcards=cards)

    return jsonify(cards)


@app.route("/api/download/notes", methods=["POST"])
def download_notes():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    fmt = (data.get("format", "txt") or "txt").lower()
    title = (data.get("title", "Lecture Notes") or "Lecture Notes")

    if fmt not in ("txt", "pdf"):
        return jsonify({"error": "Invalid format. Use 'txt' or 'pdf'."}), 400

    try:
        if fmt == "pdf":
            content = notes_to_pdf(notes, title)
            mimetype = "application/pdf"
            name = "lecture_notes.pdf"
        else:
            content = notes_to_txt(notes, title)
            mimetype = "text/plain"
            name = "lecture_notes.txt"
    except AppError as exc:
        return _handle_app_error(exc)
    except Exception as exc:
        logger.exception("export_failed fmt=%s", fmt)
        return error_response(exc)

    return send_file(
        BytesIO(content),
        mimetype=mimetype,
        as_attachment=True,
        download_name=name,
    )


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_):
    return jsonify({"error": "File too large. Max 50MB."}), 413


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    if not _frontend_built():
        return jsonify({"service": "LectureMind AI", "status": "ok"}), 404
    return send_from_directory(STATIC_FOLDER, "index.html")


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "Something went wrong. Please try again."}), 500


# --------------------------------------------------------------------------
# Frontend (production build served by Flask)
# --------------------------------------------------------------------------

def _frontend_built() -> bool:
    return STATIC_FOLDER.is_dir() and (STATIC_FOLDER / "index.html").is_file()


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if not _frontend_built():
        return jsonify(
            {
                "service": "LectureMind AI",
                "status": "ok",
                "message": "API is running. Build the frontend for the UI.",
            }
        )
    if path and (STATIC_FOLDER / path).is_file():
        return send_from_directory(STATIC_FOLDER, path)
    return send_from_directory(STATIC_FOLDER, "index.html")


if __name__ == "__main__":
    app.run(debug=not IS_PRODUCTION, host="0.0.0.0", port=5000)