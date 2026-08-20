"""Tests for GET /api/health."""


def test_health_returns_ok(app):
    resp = app.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "service": "LectureMind AI"}
