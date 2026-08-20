from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .cms_core import CMSEngine
from .cmsc_exchange import DEFAULT_FEE_RATE, quote_cmsc
from .cmsc_payment import CMSCPaymentStore

router = APIRouter(prefix='/api/exchange/cmsc/payment', tags=['cmsc-payment'])
_engine = CMSEngine()
_store = CMSCPaymentStore(_engine)

class PaymentIntentPayload(BaseModel):
    amount_cmsc: float = Field(gt=0)
    currency: str
    fee_rate: float | None = Field(default=None, ge=0, le=0.25)

class PaymentConfirmationPayload(BaseModel):
    intent_id: str
    provider: str
    provider_reference: str
    paid_amount: float = Field(gt=0)
    currency: str

def _user_email(request: Request) -> str:
    email = request.session.get('user_email')
    if not email:
        raise HTTPException(status_code=401, detail='Требуется авторизация.')
    return str(email)

def _webhook_secret() -> str:
    secret = os.getenv('CMSC_PAYMENT_WEBHOOK_SECRET', '').strip()
    if not secret:
        raise HTTPException(status_code=503, detail='Payment webhook secret не настроен.')
    return secret

def _verify_signature(raw_body: bytes, signature: str, secret: str) -> None:
    supplied = signature.strip().removeprefix('sha256=')
    expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail='Недействительная подпись payment webhook.')

@router.post('/intent')
def create_intent(payload: PaymentIntentPayload, request: Request) -> dict[str, Any]:
    email = _user_email(request)
    fee_rate = DEFAULT_FEE_RATE if payload.fee_rate is None else payload.fee_rate
    quote = quote_cmsc(payload.amount_cmsc, payload.currency, fee_rate)
    intent_id = f'cmsc_{secrets.token_urlsafe(18)}'
    return _store.create(email, quote, intent_id)

@router.post('/confirm')
async def confirm_payment(request: Request, x_cmsc_signature: str = Header(default='')) -> dict[str, Any]:
    raw_body = await request.body()
    _verify_signature(raw_body, x_cmsc_signature, _webhook_secret())
    try:
        data = json.loads(raw_body.decode('utf-8'))
        payload = PaymentConfirmationPayload.model_validate(data)
        return _store.confirm(payload.intent_id, payload.provider, payload.provider_reference, payload.paid_amount, payload.currency)
    except HTTPException:
        raise
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
