from fastapi.testclient import TestClient

from backend.main import app


def test_public_login_page_loads():
    client = TestClient(app)
    response = client.get("/login")
    assert response.status_code == 200


def test_dashboard_requires_authentication():
    client = TestClient(app)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (302, 303, 401)


def test_bot_simulation_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/api/bot/simulate",
        json={"market_data": [100.0, 100.5], "ai_stream": [0.1, 0.2]},
    )
    assert response.status_code == 401
