import pytest

from backend.exchange_service import ExchangeService


class FakeClient:
    def __init__(self):
        self.markets = {"BTC/USDT": {"limits": {"amount": {"min": 0.001}}}}
        self.fees = {"trading": {"taker": 0.001}}
        self.created = []
        self.cancelled = []

    def amount_to_precision(self, symbol, amount):
        return f"{amount:.6f}"

    def fetch_ticker(self, symbol):
        return {"last": 100000}

    def create_order(self, *args):
        self.created.append(args)
        return {"id": "created"}

    def cancel_order(self, *args):
        self.cancelled.append(args)
        return {"id": "cancelled"}


def test_exchange_service_does_not_persist_credentials(monkeypatch):
    service = ExchangeService()
    fake = FakeClient()

    monkeypatch.setattr(service, "_exchange_class", staticmethod(lambda name: ("binance", lambda config: fake)))
    monkeypatch.setattr(fake, "load_markets", lambda: None, raising=False)
    monkeypatch.setattr(fake, "fetch_balance", lambda: {"free": {"USDT": 100}}, raising=False)

    service.connect("user-1", "binance", "SECRET_API_KEY", "SECRET_API_SECRET")
    stored = service.get("user-1")

    assert "SECRET_API_KEY" not in repr(stored)
    assert "SECRET_API_SECRET" not in repr(stored)
    assert stored["api_key_hint"] == "SECR..._KEY"


def test_exchange_service_blocks_order_in_shadow(monkeypatch):
    service = ExchangeService()
    fake = FakeClient()
    monkeypatch.setattr(service, "get", lambda user_id: {"client": fake})
    monkeypatch.setenv("TRADING_MODE", "shadow")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")

    with pytest.raises(PermissionError):
        service.create_order("user-1", "BTC/USDT", "market", "buy", 0.001)

    assert fake.created == []


def test_exchange_service_blocks_cancel_in_demo(monkeypatch):
    service = ExchangeService()
    fake = FakeClient()
    monkeypatch.setattr(service, "get", lambda user_id: {"client": fake})
    monkeypatch.setenv("TRADING_MODE", "demo")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")

    with pytest.raises(PermissionError):
        service.cancel_order("user-1", "order-1", "BTC/USDT")

    assert fake.cancelled == []
