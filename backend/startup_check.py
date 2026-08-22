"""Startup validation helpers for CMS backend."""

import os


def validate_startup_environment() -> dict:
    env = os.getenv("APP_ENV", "development").lower()
    secret = os.getenv("SECRET_KEY", "")

    errors = []
    warnings = []

    if env == "production" and not secret:
        errors.append("SECRET_KEY is required in production")

    if not secret:
        warnings.append("Using development secret configuration")

    return {
        "ok": not errors,
        "environment": env,
        "errors": errors,
        "warnings": warnings,
    }


def assert_startup_ready() -> None:
    result = validate_startup_environment()
    if not result["ok"]:
        raise RuntimeError("Startup validation failed: " + "; ".join(result["errors"]))
