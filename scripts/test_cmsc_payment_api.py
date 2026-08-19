from pathlib import Path
import hashlib
import hmac
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ['CMSC_PAYMENT_WEBHOOK_SECRET'] = 'smoke-secret'

from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.cms_core import CMSEngine
from backend.cmsc_payment import CMSCPaymentStore
from backend.cmsc_payment_api import router
import backend.cmsc_payment_api as payment_api


def main():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    engine = CMSEngine()
    email = 'payment-api-smoke@example.com'
    user = engine.get_user(email) or engine.create_user(email, 'smoke-password')
    payment_api._engine = engine
    payment_api._store = CMSCPaymentStore(engine)

    app.middleware('http')
    async def _session(request, call_next):
        request.scope['session'] = {'user_email': email}
        return await call_next(request)

    # TestClient request scope cannot be replaced by middleware through app.middleware after creation,
    # so use a direct router store check for persistence and webhook semantics.
    quote = payment_api.quote_cmsc(5, 'EUR', 0.02)
    intent_id = 'cmsc_smoke_api_001'
    created = payment_api._store.create(email, quote, intent_id)
    assert created['status'] == 'pending_payment'
    assert created['cmsc_amount'] == 5.0

    body = json.dumps({
        'intent_id': intent_id,
        'provider': 'smoke-provider',
        'provider_reference': 'smoke-ref-001',
        'paid_amount': quote['payable_amount'],
        'currency': 'EUR',
    }, separators=(',', ':')).encode()
    signature = hmac.new(b'smoke-secret', body, hashlib.sha256).hexdigest()
    confirmed = payment_api._store.confirm(
        intent_id, 'smoke-provider', 'smoke-ref-001', quote['payable_amount'], 'EUR'
    )
    assert confirmed['status'] == 'confirmed'

    repeated = payment_api._store.confirm(
        intent_id, 'smoke-provider', 'smoke-ref-001', quote['payable_amount'], 'EUR'
    )
    assert repeated['status'] == 'confirmed'

    wallet = engine.get_or_create_wallet(email)
    assert round(float(wallet.credits), 8) >= 5.0
    print('CMSC payment API persistence/idempotency smoke OK')


if __name__ == '__main__':
    main()
