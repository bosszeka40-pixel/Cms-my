"""Request-level safety helpers for authenticated, non-live trading endpoints."""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

_RATE_LIMIT_LOCK = Lock()
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def require_user(request: Request) -> str:
    """Require an authenticated session and return the user email."""
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    return str(email)


def require_virtual_execution(request: Request) -> str:
    """Require authentication and explicitly reject LIVE execution for virtual APIs."""
    email = require_user(request)
    mode = str(request.headers.get("X-Trading-Mode", "virtual")).strip().lower()
    if mode == "live":
        raise HTTPException(status_code=403, detail="LIVE execution is not permitted by this endpoint.")
    return email


def enforce_rate_limit(key: str, *, limit: int = 30, window_seconds: float = 60.0) -> None:
    """Apply a small process-local sliding-window limit to expensive API operations.

    This is intentionally a safety backstop, not a replacement for a distributed
    gateway/rate limiter in production deployments.
    """
    if not key or limit <= 0 or window_seconds <= 0:
        raise ValueError("Invalid rate-limit configuration.")
    now = monotonic()
    cutoff = now - window_seconds
    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="Слишком много запросов. Повторите позже.")
        bucket.append(now)


def client_safe_error(message: str = "Операция не выполнена.") -> HTTPException:
    """Return a stable client-facing error without leaking provider internals."""
    return HTTPException(status_code=502, detail=message)
