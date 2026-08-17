"""Request-level safety helpers for authenticated, non-live trading endpoints."""
from __future__ import annotations

from fastapi import HTTPException, Request


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


def client_safe_error(message: str = "Операция не выполнена.") -> HTTPException:
    """Return a stable client-facing error without leaking provider internals."""
    return HTTPException(status_code=502, detail=message)
