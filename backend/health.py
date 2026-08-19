"""Health, readiness, and small deployment-safe integration probes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .market_history import ensure_table
from .marketplace_billing import purchase_strategy_with_cmsc

router = APIRouter(tags=["health"])


class StrategyPurchasePayload(BaseModel):
    plugin_name: str
    duration_days: int = 15


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


@router.post("/api/strategies/purchase")
def purchase_strategy(payload: StrategyPurchasePayload, request):
    """Charge paid strategy purchases from the internal CMSC wallet."""
    from .main import _strategy_performance, engine

    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        performance = _strategy_performance()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось проверить цену стратегии: {exc}") from exc

    result = performance.get(payload.plugin_name)
    if not result:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")

    try:
        purchase = purchase_strategy_with_cmsc(
            engine,
            email,
            payload.plugin_name,
            result.get("price_eur", 0.0),
            payload.duration_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not purchase:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")
    return purchase
