"""Security helpers: rate limiting and safe error responses.

The application intentionally does not expose exception internals, Groq
response payloads, or stack traces to API clients. All server-side failures
are logged in full and reduced to a safe, actionable message for the client.
"""

import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Optional, Tuple

from flask import jsonify, request

from utils.logging import get_logger

logger = get_logger("lecturemind.security")


class RateLimitExceeded(Exception):
    """Raised when a client exceeds its per-window request quota."""


_hits: dict[str, deque] = defaultdict(deque)
_last_cleanup = time.monotonic()
_CLEANUP_INTERVAL = 600


def _cleanup(now: float) -> None:
    """Drop entries that have not been touched within the cleanup window."""
    global _last_cleanup
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    for key in [k for k, q in _hits.items() if not q or now - q[-1] > _CLEANUP_INTERVAL]:
        _hits.pop(key, None)


def check_rate_limit(key: str, limit: int, window: float) -> None:
    """Enforce a sliding-window limit. `limit <= 0` disables the limit."""
    if limit <= 0:
        return
    now = time.monotonic()
    _cleanup(now)
    queue = _hits[key]
    while queue and now - queue[0] > window:
        queue.popleft()
    if len(queue) >= limit:
        raise RateLimitExceeded()
    queue.append(now)


def rate_limit(limit: int, window: float, key_prefix: str) -> Callable:
    """Decorator that rate-limits a Flask route per client IP."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            check_rate_limit(f"{key_prefix}:{ip}", limit, window)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _safe_message(exc: Exception) -> Tuple[int, str]:
    """Map known failure types to a safe client-facing message."""
    from groq import APIConnectionError, APITimeoutError, RateLimitError

    if isinstance(exc, RateLimitExceeded):
        return 429, "Too many requests. Please wait a moment and try again."
    if isinstance(exc, RateLimitError):
        return 503, "The AI service is busy. Please wait a moment and try again."
    if isinstance(exc, APITimeoutError):
        return 504, "The AI service timed out. Please try again."
    if isinstance(exc, APIConnectionError):
        return 502, "Could not reach the AI service. Please try again."
    return 500, "Something went wrong. Please try again."


def error_response(exc: Exception) -> "flask.Response":
    """Build a sanitized JSON error response and log the real error server-side."""
    status, message = _safe_message(exc)
    logger.warning("request_failed status=%d error=%s", status, exc)
    return jsonify({"error": message}), status


class AppError(Exception):
    """An expected application error with a safe client-facing message."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status