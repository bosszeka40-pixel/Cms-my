"""Reusable HTTP security helpers for the FastAPI application.

This module is deliberately framework-light so it can be tested independently
before being installed into the application middleware stack.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Small in-process sliding-window limiter for sensitive endpoints."""

    def __init__(self, limit: int = 10, window_seconds: int = 60):
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            events = self._events[key]
            cutoff = current - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(current)
            return True


def issue_csrf_token(secret: str, session_id: str) -> str:
    """Create a deterministic, signed CSRF token for a session."""
    if not secret or not session_id:
        raise ValueError("secret and session_id are required")
    nonce = secrets.token_urlsafe(18)
    payload = f"{session_id}:{nonce}".encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"{nonce}.{signature}"


def verify_csrf_token(secret: str, session_id: str, token: str) -> bool:
    if not secret or not session_id or not token or "." not in token:
        return False
    nonce, signature = token.split(".", 1)
    if not nonce or not signature:
        return False
    payload = f"{session_id}:{nonce}".encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def client_key(client_host: str | None, user_email: str | None = None) -> str:
    """Prefer authenticated identity while retaining an IP fallback."""
    return f"user:{user_email}" if user_email else f"ip:{client_host or 'unknown'}"
