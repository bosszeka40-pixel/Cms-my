from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

import backend.cmsc_exchange as exchange
from backend.health import router


def build_client():
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key='ci-smoke-secret')
    app.include_router(router)
    return TestClient(app)


def main():
    client = build_client()

    for path in ('/api/exchange/cmsc/quote', '/api/exchange/cmsc/intent'):
        response = client.post(path, json={'amount_cmsc': 10, 'currency': 'EUR'})
        assert response.status_code == 401, (path, response.status_code, response.text)

    original_rate = exchange.current_eur_rate
    exchange.current_eur_rate = lambda currency: 1.0
    try:
        quote = exchange.quote_cmsc(100, ' eur ', 0.02)
        assert quote['currency'] == 'EUR'
        assert quote['gross_payment'] == 100.0
        assert quote['fee_amount'] == 2.0
        assert quote['payable_amount'] == 102.0
    finally:
        exchange.current_eur_rate = original_rate

    for _ in range(19):
        response = client.post('/api/exchange/cmsc/quote', json={'amount_cmsc': 10, 'currency': 'EUR'})
        assert response.status_code == 401, response.status_code
    response = client.post('/api/exchange/cmsc/quote', json={'amount_cmsc': 10, 'currency': 'EUR'})
    assert response.status_code == 429, (response.status_code, response.text)

    print('CMSC exchange security smoke OK')


if __name__ == '__main__':
    main()
