from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.health import router


def main():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Anonymous requests must still be rejected as unauthorized before they can
    # reach the business operation. The rate limiter must also eventually emit 429.
    for _ in range(20):
        response = client.post('/api/exchange/cmsc/quote', json={'amount_cmsc': 10, 'currency': 'EUR'})
        assert response.status_code in (401, 429), response.text

    responses = [
        client.post('/api/exchange/cmsc/intent', json={'amount_cmsc': 10, 'currency': 'EUR'})
        for _ in range(6)
    ]
    assert responses[-1].status_code == 429, [r.status_code for r in responses]

    print('CMSC exchange rate-limit smoke OK')


if __name__ == '__main__':
    main()
