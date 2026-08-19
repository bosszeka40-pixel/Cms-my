from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.health import router


def main():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    for path in ('/api/exchange/cmsc/quote', '/api/exchange/cmsc/intent'):
        response = client.post(path, json={'amount_cmsc': 10, 'currency': 'USD'})
        assert response.status_code == 401, (path, response.status_code, response.text)

    print('CMSC exchange API auth smoke OK')


if __name__ == '__main__':
    main()
