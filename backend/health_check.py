import importlib
import os


CRITICAL_MODULES = (
    "backend.bot",
    "backend.risk_management",
    "backend.live_trading_guard",
    "backend.trading_execution_gate",
)


def startup_health_check() -> dict:
    """Return CMS startup readiness information."""
    checks = {}

    for module_name in CRITICAL_MODULES:
        try:
            importlib.import_module(module_name)
            checks[module_name] = "ok"
        except Exception as exc:  # pragma: no cover
            checks[module_name] = f"error: {exc.__class__.__name__}"

    production = os.getenv("APP_ENV", "development").lower() == "production"
    secret_ok = bool(os.getenv("SECRET_KEY"))

    if production and not secret_ok:
        checks["secret_key"] = "missing"
    else:
        checks["secret_key"] = "ok"

    ready = all(value == "ok" for value in checks.values())

    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
