import importlib

import pytest


def _load_main(monkeypatch, app_env):
    monkeypatch.setenv("APP_ENV", app_env)
    import backend.main as main
    return importlib.reload(main)


def test_dev_admin_bypass_is_disabled_in_production(monkeypatch):
    main = _load_main(monkeypatch, "production")
    assert main.DEV_ADMIN_BYPASS_ENABLED is False


def test_dev_admin_bypass_requires_non_production_environment(monkeypatch):
    main = _load_main(monkeypatch, "development")
    assert main.DEV_ADMIN_BYPASS_ENABLED is True


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    import backend.main as main
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured in production"):
        importlib.reload(main)
