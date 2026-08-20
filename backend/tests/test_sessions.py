"""Tests for the in-memory session store: create/get, TTL expiry, sweeping."""

import time

from services.session_store import store


def _create_session(transcript="The quick brown fox jumps over the lazy dog."):
    return store.create(
        transcript=transcript,
        segments=[{"start": 0.0, "end": 1.0, "text": transcript}],
        language="en",
        filepath="",
    )


def _expire(session_id):
    store._sessions[session_id]["last_accessed"] = time.time() - store._ttl - 60


def test_create_and_get(app):
    session_id = _create_session()
    session = store.get(session_id)
    assert session is not None
    assert session["transcript"].startswith("The quick brown fox")
    assert session["language"] == "en"
    assert session["notes"] is None
    assert session["quiz"] is None
    assert session["flashcards"] is None
    assert store.get("does-not-exist") is None


def test_get_refreshes_last_accessed(app):
    session_id = _create_session()
    first = store.get(session_id)["last_accessed"]
    time.sleep(0.01)
    second = store.get(session_id)["last_accessed"]
    assert second >= first


def test_get_returns_none_and_deletes_file_when_expired(app, tmp_path):
    audio_file = tmp_path / "clip.mp3"
    audio_file.write_bytes(b"ID3" + b"\x00" * 16)

    session_id = store.create(
        transcript="expired transcript",
        segments=[],
        language="en",
        filepath=str(audio_file),
    )
    _expire(session_id)

    assert store.get(session_id) is None
    assert session_id not in store._sessions
    assert not audio_file.exists()  # underlying file cleaned up with session


def test_maybe_sweep_removes_expired_keeps_active(app, tmp_path):
    expired_file = tmp_path / "expired.mp3"
    expired_file.write_bytes(b"ID3" + b"\x00" * 16)

    expired_sid = store.create(
        transcript="old",
        segments=[],
        language="en",
        filepath=str(expired_file),
    )
    active_sid = _create_session()
    _expire(expired_sid)

    # Backdate the last-sweep timestamp so maybe_sweep actually runs.
    store._last_sweep = time.monotonic() - 3600
    removed = store.maybe_sweep()

    assert removed == 1
    assert expired_sid not in store._sessions
    assert active_sid in store._sessions
    assert store.get(active_sid) is not None
    assert not expired_file.exists()
