"""Shared pytest fixtures and environment setup for the LectureMind AI backend.

Environment variables MUST be set before the ``app`` module (and its
``config`` import) is first imported, because:

* ``config.py`` reads UPLOAD_FOLDER / GROQ_API_KEY / CORS_ORIGINS at import
  time into module constants;
* the rate-limit route decorators capture RATE_LIMIT_TRANSCRIBE and
  RATE_LIMIT_GENERATE at *decoration* (import) time.

Setting the limits to 0 disables rate limiting for the whole suite; the
dedicated rate-limit test re-enables enforcement by monkeypatching
``utils.security.check_rate_limit`` directly (the decorator resolves that
name at call time).
"""

import os
import tempfile
import time

_UPLOAD_DIR = tempfile.mkdtemp(prefix="lecturemind-test-uploads-")

os.environ["UPLOAD_FOLDER"] = _UPLOAD_DIR
os.environ["GROQ_API_KEY"] = "test-key-never-used"
os.environ["CORS_ORIGINS"] = "*"
os.environ["RATE_LIMIT_TRANSCRIBE"] = "0"
os.environ["RATE_LIMIT_GENERATE"] = "0"
os.environ["MAX_CONTENT_LENGTH"] = str(50 * 1024 * 1024)  # default 50MB
os.environ["RENDER"] = "false"
os.environ["FLASK_ENV"] = "test"

import pytest  # noqa: E402

import app as app_module  # noqa: E402
import utils.security  # noqa: E402
from config import UPLOAD_FOLDER  # noqa: E402
from services.session_store import store  # noqa: E402


@pytest.fixture()
def app(monkeypatch):
    """Yield the Flask test client with pristine in-memory state.

    Resets the session store and the rate-limit hit counters between tests
    so state never leaks from one test into another.
    """
    store._sessions.clear()
    # Backdate so maybe_sweep() actually runs on the next request, even on a
    # system whose monotonic clock is small (fresh boot).
    store._last_sweep = time.monotonic() - 3600
    utils.security._hits.clear()

    # Belt and braces: the decorators captured the limits at import time
    # (0 == disabled), but keep the module attrs consistent for anything
    # that reads them directly.
    monkeypatch.setattr(app_module, "RATE_LIMIT_TRANSCRIBE", 0)
    monkeypatch.setattr(app_module, "RATE_LIMIT_GENERATE", 0)

    with app_module.app.test_client() as client:
        yield client

    store._sessions.clear()


@pytest.fixture()
def fake_audio_mp3():
    """Bytes of a valid-looking MP3: ID3 magic plus payload (>= 12 bytes)."""
    return b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 32


@pytest.fixture()
def fake_invalid_audio():
    """Bytes that do not match any allowed audio container signature."""
    return b"not an audio file........."
