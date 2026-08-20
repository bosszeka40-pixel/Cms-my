from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_public_pages_are_registered():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {200, 302, 307}


def test_protected_bot_simulation_fails_closed_without_session():
    response = client.post(
        "/api/bot/simulate",
        json={"market_data": [1.0, 1.1, 1.2], "ai_stream": [0.1, 0.2, 0.3]},
    )
    assert response.status_code == 401


def test_protected_market_data_fails_closed_without_session():
    response = client.get("/api/market/data")
    assert response.status_code == 401


def test_protected_trading_history_fails_closed_without_session():
    response = client.get("/api/trading/history")
    assert response.status_code == 401
