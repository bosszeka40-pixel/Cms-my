"""Health, readiness, and small deployment-safe integration probes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .market_history import ensure_table
from .cmsc_exchange import DEFAULT_FEE_RATE, create_payment_intent, quote_cmsc
from .cmsc_payment_api import router as cmsc_payment_router
from .rate_limit import cmsc_intent_rate_limit, cmsc_quote_rate_limit

router = APIRouter(tags=["health"])
router.include_router(cmsc_payment_router)

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

def _safe_bad_gateway(message: str) -> HTTPException:
    return HTTPException(status_code=502, detail=message)

@router.post("/api/exchange/cmsc/quote")
def cmsc_exchange_quote(payload: CmscExchangePayload, request: Request, _: None = Depends(cmsc_quote_rate_limit)):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return quote_cmsc(payload.amount_cmsc, payload.currency, _cmsc_exchange_fee_rate())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _safe_bad_gateway("Не удалось получить актуальный курс.") from exc

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
        raise _safe_bad_gateway("Не удалось создать платёжный intent.") from exc
