"""In-memory session store with TTL expiry and uploaded-file cleanup.

Sessions keep transcripts and generated material for the duration of a
visitor's workflow. They are intentionally short-lived: expired sessions are
swept periodically and their uploaded audio file is deleted from disk, which
keeps memory and ephemeral-disk usage bounded on the free Render tier.

A single-process, single-worker deployment is required (see README) so that
the in-memory store is consistent across requests.
"""

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from config import SESSION_CLEANUP_INTERVAL, SESSION_TTL_SECONDS
from utils.logging import get_logger

logger = get_logger("lecturemind.session")

_Session = Dict[str, Any]


class SessionStore:
    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._sessions: Dict[str, _Session] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def create(
        self,
        transcript: str,
        segments: list,
        language: str,
        filepath: str,
    ) -> str:
        session_id = str(uuid.uuid4())
        now = time.time()
        with self._lock:
            self._sessions[session_id] = {
                "transcript": transcript,
                "segments": segments,
                "language": language,
                "notes": None,
                "quiz": None,
                "flashcards": None,
                "filepath": filepath,
                "created_at": now,
                "last_accessed": now,
            }
        logger.info(
            "session_created session_id=%s transcript_chars=%d segments=%d",
            session_id,
            len(transcript),
            len(segments),
        )
        return session_id

    def get(self, session_id: str) -> Optional[_Session]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if time.time() - session["last_accessed"] > self._ttl:
                self._delete_locked(session_id, session)
                logger.info("session_expired session_id=%s", session_id)
                return None
            session["last_accessed"] = time.time()
            return session

    def update(self, session_id: str, **fields: Any) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.update(fields)

    def _delete_locked(self, session_id: str, session: _Session) -> None:
        self._sessions.pop(session_id, None)
        filepath = session.get("filepath")
        if filepath:
            try:
                Path(filepath).unlink(missing_ok=True)
            except OSError:
                logger.warning("session_file_cleanup_failed session_id=%s", session_id)

    def maybe_sweep(self) -> int:
        """Sweep expired sessions at most once per interval. Returns count removed."""
        now = time.monotonic()
        if now - self._last_sweep < SESSION_CLEANUP_INTERVAL:
            return 0
        self._last_sweep = now
        expired = 0
        with self._lock:
            cutoff = time.time() - self._ttl
            for sid in [s for s, sess in self._sessions.items() if sess["last_accessed"] < cutoff]:
                session = self._sessions.pop(sid, None)
                if session is not None:
                    expired += 1
                    self._delete_locked(sid, session)
        if expired:
            logger.info("session_sweep removed=%d active=%d", expired, len(self._sessions))
        return expired


store = SessionStore()