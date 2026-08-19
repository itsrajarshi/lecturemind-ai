"""Tests for POST /api/transcribe: validation, signature sniffing, uploads."""

import io

import app as app_module
from config import UPLOAD_FOLDER
from services.session_store import store


def _post_audio(client, filename, content):
    data = {"audio": (io.BytesIO(content), filename)}
    return client.post("/api/transcribe", data=data, content_type="multipart/form-data")


def _files_in_upload_dir():
    return set(UPLOAD_FOLDER.iterdir())


def test_transcribe_without_file_returns_400(app):
    resp = app.post("/api/transcribe", data={})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "No audio file provided"}


def test_transcribe_rejects_disallowed_extension(app):
    resp = _post_audio(app, "lecture.txt", b"just some plain text")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_transcribe_rejects_wrong_magic_bytes(app, fake_invalid_audio):
    before = _files_in_upload_dir()
    resp = _post_audio(app, "evil.mp3", fake_invalid_audio)
    assert resp.status_code == 400
    assert "error" in resp.get_json()
    # The rejected upload must not linger on disk.
    assert _files_in_upload_dir() == before


def test_transcribe_success(app, monkeypatch, fake_audio_mp3):
    monkeypatch.setattr(
        app_module,
        "transcribe_audio",
        lambda path: {
            "text": "Hello world",
            "language": "en",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}],
        },
    )
    before = _files_in_upload_dir()
    resp = _post_audio(app, "clip.mp3", fake_audio_mp3)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["session_id"]
    assert body["transcript"] == "Hello world"
    assert body["language"] == "en"
    assert body["segments"] == [{"start": 0.0, "end": 1.0, "text": "Hello world"}]

    # The uploaded file was written into the temp upload folder...
    new_files = _files_in_upload_dir() - before
    assert len(new_files) == 1
    assert new_files.pop().read_bytes().startswith(b"ID3")
    # ...and a session was created for it.
    assert len(store._sessions) == 1


def test_transcribe_empty_result_returns_422(app, monkeypatch, fake_audio_mp3):
    monkeypatch.setattr(
        app_module,
        "transcribe_audio",
        lambda path: {"text": "", "language": "en", "segments": []},
    )
    resp = _post_audio(app, "clip.mp3", fake_audio_mp3)
    assert resp.status_code == 422
    assert resp.get_json()["error"] == (
        "No speech detected in the audio. Please try a clearer recording."
    )


def test_transcribe_file_too_large_returns_413(app, fake_audio_mp3):
    flask_app = app_module.app
    flask_app.config["MAX_CONTENT_LENGTH"] = 200
    try:
        resp = _post_audio(app, "huge.mp3", fake_audio_mp3 * 100)
        assert resp.status_code == 413
        assert resp.get_json() == {"error": "File too large. Max 50MB."}
    finally:
        flask_app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
