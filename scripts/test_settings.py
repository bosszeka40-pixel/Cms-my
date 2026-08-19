import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app, engine


def main():
    email = "settings-smoke@example.invalid"
    password = "settings-smoke-password"
    existing = engine.get_user(email)
    if existing:
        raise RuntimeError("Settings smoke user already exists; use a clean CI database.")

    engine.create_user(email, password)
    client = TestClient(app)

    login = client.post("/login", data={"username": email, "password": password}, follow_redirects=False)
    assert login.status_code == 302, login.text
    assert login.headers["location"] == "/dashboard"

    settings = client.get("/settings")
    assert settings.status_code == 200, settings.text
    assert "Настройки аккаунта" in settings.text
    assert "Светлая" in settings.text
    assert "Тёмная" in settings.text

    save = client.post("/settings", data={"theme": "dark"}, follow_redirects=False)
    assert save.status_code == 200, save.text
    assert "Настройки аккаунта сохранены." in save.text

    saved = client.get("/settings")
    assert saved.status_code == 200, saved.text
    assert 'option value="dark" selected' in saved.text

    invalid = client.post("/settings", data={"theme": "invalid"})
    assert invalid.status_code == 200, invalid.text
    assert "Выберите доступную тему оформления." in invalid.text

    print("Settings theme path OK")


if __name__ == "__main__":
    main()
