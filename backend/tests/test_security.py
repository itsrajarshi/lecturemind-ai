"""Tests for security behavior: 404/405 handling, headers, rate limiting."""

import io

import app as app_module
import utils.security


def test_unknown_api_route_returns_json_404(app):
    resp = app.get("/api/nonexistent-route")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Not found"}


def test_unknown_api_route_does_not_leak_spa(app):
    """Even with the frontend unbuilt, API paths must not return the SPA shell."""
    resp = app.get("/api/definitely-not-a-route")
    assert resp.status_code == 404
    assert "service" not in resp.get_json()


def test_wrong_method_returns_405_json(app):
    resp = app.post("/api/health")
    assert resp.status_code == 405
    assert resp.get_json() == {"error": "Method not allowed"}


def test_cors_header_present(app):
    resp = app.get("/api/health", headers={"Origin": "https://example.com"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") is not None


def test_content_type_options_header_present(app):
    resp = app.get("/api/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_transcribe_rate_limit_enforced(app, monkeypatch, fake_audio_mp3):
    real_check = utils.security.check_rate_limit

    def forced_check(key, limit, window):
        # The decorator captured the disabled limit (0); enforce 2/hour here.
        real_check(key, 2, window)

    monkeypatch.setattr(utils.security, "check_rate_limit", forced_check)
    monkeypatch.setattr(app_module, "RATE_LIMIT_TRANSCRIBE", 2)
    monkeypatch.setattr(
        app_module,
        "transcribe_audio",
        lambda path: {"text": "Hello", "language": "en", "segments": []},
    )

    def _post():
        data = {"audio": (io.BytesIO(fake_audio_mp3), "clip.mp3")}
        return app.post("/api/transcribe", data=data, content_type="multipart/form-data")

    assert _post().status_code == 200
    assert _post().status_code == 200

    third = _post()
    assert third.status_code == 429
    assert "Too many requests" in third.get_json()["error"]