import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from io import BytesIO
from werkzeug.exceptions import RequestEntityTooLarge

from config import BASE_DIR, MAX_CONTENT_LENGTH, UPLOAD_FOLDER
from services.export_service import notes_to_pdf, notes_to_txt
from services.groq_service import generate_flashcards, generate_notes, generate_quiz
from services.whisper_service import transcribe_audio
from utils.file_validator import allowed_file, safe_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app, resources={r"/api/*": {"origins": "*"}})

STATIC_FOLDER = BASE_DIR / "static"

# In-memory session store (no SQLite required for demo)
sessions: dict[str, dict] = {}


def _session_id() -> str:
    header = request.headers.get("X-Session-Id", "")
    if header:
        return header
    data = request.get_json(silent=True) or {}
    return data.get("session_id", "")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "LectureMind AI"})


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["audio"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file. Allowed: MP3, WAV, M4A"}), 400

    session_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{session_id}.{ext}"
    filepath = UPLOAD_FOLDER / safe_filename(filename)
    file.save(filepath)

    try:
        result = transcribe_audio(str(filepath))
    except Exception as exc:
        return jsonify({"error": f"Transcription failed: {exc}"}), 500

    sessions[session_id] = {
        "transcript": result["text"],
        "segments": result["segments"],
        "language": result["language"],
        "notes": "",
        "quiz": None,
        "flashcards": None,
        "filepath": str(filepath),
    }

    return jsonify(
        {
            "session_id": session_id,
            "transcript": result["text"],
            "language": result["language"],
            "segments": result["segments"],
        }
    )


@app.route("/api/generate/notes", methods=["POST"])
def notes():
    data = request.get_json(silent=True) or {}
    session_id = _session_id() or data.get("session_id")
    transcript = data.get("transcript")

    if session_id and session_id in sessions:
        transcript = sessions[session_id]["transcript"]
    if not transcript:
        return jsonify({"error": "Transcript required"}), 400

    try:
        notes_md = generate_notes(transcript)
    except Exception as exc:
        return jsonify({"error": f"Notes generation failed: {exc}"}), 500

    if session_id in sessions:
        sessions[session_id]["notes"] = notes_md

    return jsonify({"notes": notes_md, "format": "markdown"})


@app.route("/api/generate/quiz", methods=["POST"])
def quiz():
    data = request.get_json(silent=True) or {}
    session_id = _session_id() or data.get("session_id")
    transcript = data.get("transcript")

    if session_id and session_id in sessions:
        transcript = sessions[session_id]["transcript"]
    if not transcript:
        return jsonify({"error": "Transcript required"}), 400

    try:
        quiz_data = generate_quiz(transcript)
    except Exception as exc:
        return jsonify({"error": f"Quiz generation failed: {exc}"}), 500

    if session_id in sessions:
        sessions[session_id]["quiz"] = quiz_data

    return jsonify(quiz_data)


@app.route("/api/generate/flashcards", methods=["POST"])
def flashcards():
    data = request.get_json(silent=True) or {}
    session_id = _session_id() or data.get("session_id")
    transcript = data.get("transcript")

    if session_id and session_id in sessions:
        transcript = sessions[session_id]["transcript"]
    if not transcript:
        return jsonify({"error": "Transcript required"}), 400

    try:
        cards = generate_flashcards(transcript)
    except Exception as exc:
        return jsonify({"error": f"Flashcard generation failed: {exc}"}), 500

    if session_id in sessions:
        sessions[session_id]["flashcards"] = cards

    return jsonify(cards)


@app.route("/api/download/notes", methods=["POST"])
def download_notes():
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    fmt = data.get("format", "txt").lower()
    title = data.get("title", "Lecture Notes")

    if not notes:
        return jsonify({"error": "Notes content required"}), 400

    if fmt == "pdf":
        content = notes_to_pdf(notes, title)
        return send_file(
            BytesIO(content),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="lecture_notes.pdf",
        )

    content = notes_to_txt(notes, title)
    return send_file(
        BytesIO(content),
        mimetype="text/plain",
        as_attachment=True,
        download_name="lecture_notes.txt",
    )


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_):
    return jsonify({"error": "File too large. Max 50MB."}), 413


def _frontend_built() -> bool:
    return STATIC_FOLDER.is_dir() and (STATIC_FOLDER / "index.html").is_file()


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the React app in production (after `npm run build`)."""
    if not _frontend_built():
        return jsonify(
            {
                "service": "LectureMind AI",
                "status": "ok",
                "message": "API is running. Build frontend for the UI.",
            }
        )
    if path and (STATIC_FOLDER / path).is_file():
        return send_from_directory(STATIC_FOLDER, path)
    return send_from_directory(STATIC_FOLDER, "index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
