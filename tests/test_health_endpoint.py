from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint_available():
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert "status" in response.json()
