"""Health, readiness, and small deployment-safe integration probes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .market_history import ensure_table
from .marketplace_billing import purchase_strategy_with_cmsc
from .cmsc_exchange import DEFAULT_FEE_RATE, create_payment_intent, quote_cmsc
from .cmsc_payment_api import router as cmsc_payment_router
from .rate_limit import cmsc_intent_rate_limit, cmsc_quote_rate_limit

router = APIRouter(tags=["health"])
router.include_router(cmsc_payment_router)

class StrategyPurchasePayload(BaseModel):
    plugin_name: str
    duration_days: int = 15

class CmscExchangePayload(BaseModel):
    amount_cmsc: float
    currency: str

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/ready")
def ready() -> dict[str, str]:
    from .main import MARKET_DATABASE
    ensure_table(MARKET_DATABASE)
    return {"status": "ready"}

def _cmsc_exchange_fee_rate() -> float:
    from .main import strategy_manager
    return float(strategy_manager.config.get("cmsc_exchange_fee_rate", DEFAULT_FEE_RATE))

@router.post("/api/strategies/purchase")
def purchase_strategy(payload: StrategyPurchasePayload, request: Request):
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
        purchase = purchase_strategy_with_cmsc(engine, email, payload.plugin_name, result.get("price_eur", 0.0), payload.duration_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not purchase:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")
    return purchase

@router.post("/api/exchange/cmsc/quote")
def cmsc_exchange_quote(payload: CmscExchangePayload, request: Request, _: None = Depends(cmsc_quote_rate_limit)):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return quote_cmsc(payload.amount_cmsc, payload.currency, _cmsc_exchange_fee_rate())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить актуальный курс: {exc}") from exc

@router.post("/api/exchange/cmsc/intent")
def cmsc_exchange_intent(payload: CmscExchangePayload, request: Request, _: None = Depends(cmsc_intent_rate_limit)):
    from .main import engine
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return create_payment_intent(engine, email, payload.amount_cmsc, payload.currency, _cmsc_exchange_fee_rate())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось создать платёжный intent: {exc}") from exc
