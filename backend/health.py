"""Health and readiness probes for server deployments."""
from __future__ import annotations

from fastapi import APIRouter

from .market_history import ensure_table

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a cheap liveness signal for load balancers."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """Verify startup-critical local storage before receiving traffic."""
    from .main import MARKET_DATABASE

    ensure_table(MARKET_DATABASE)
    return {"status": "ready"}
