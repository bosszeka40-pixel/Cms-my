import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app, engine


def main():
    email = "dashboard-smoke@example.invalid"
    password = "dashboard-smoke-password"
    existing = engine.get_user(email)
    if existing:
        raise RuntimeError("Dashboard smoke user already exists; use a clean CI database.")

    user = engine.create_user(email, password)
    engine.add_wallet_credits(email, 42.5)

    client = TestClient(app)
    login = client.post("/login", data={"username": email, "password": password}, follow_redirects=False)
    assert login.status_code == 302, login.text
    assert login.headers["location"] == "/dashboard"

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert "42.50 CMSC" in dashboard.text
    assert email in dashboard.text

    print("Dashboard CMSC balance path OK")


if __name__ == "__main__":
    main()
