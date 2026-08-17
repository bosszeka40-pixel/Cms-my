"""Helpers for preventing exchange credentials from leaking through errors."""

from __future__ import annotations

from .credential_safety import SENSITIVE_KEYS


def safe_exception_message(exc: BaseException, secrets: list[str] | tuple[str, ...] = ()) -> str:
    """Return an exception message with known credentials removed."""
    message = str(exc)
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message


def safe_error_payload(exc: BaseException, secrets: list[str] | tuple[str, ...] = ()) -> dict[str, str]:
    """Build an API-safe error payload without exposing credential material."""
    return {"error": safe_exception_message(exc, secrets)}
