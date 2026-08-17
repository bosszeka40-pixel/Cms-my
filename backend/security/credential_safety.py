"""Credential-safety helpers for exchange integrations."""

from __future__ import annotations

SENSITIVE_KEYS = {
    "api_key",
    "apiKey",
    "api_secret",
    "apiSecret",
    "secret",
    "password",
    "passphrase",
}


def redact_mapping(data: dict) -> dict:
    """Return a shallow redacted copy suitable for logs/API responses."""
    return {
        key: "[REDACTED]" if key in SENSITIVE_KEYS else value
        for key, value in data.items()
    }


def mask_secret(value: str, visible: int = 4) -> str:
    """Mask a credential while retaining only a small prefix/suffix."""
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"
