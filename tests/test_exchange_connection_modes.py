from backend.exchange_service import ExchangeService


class FakeClient:
    def __init__(self, config):
        self.config = config
        self.sandbox_calls = []
        self.loaded = False
        self.balance_calls = 0

    def set_sandbox_mode(self, enabled):
        self.sandbox_calls.append(enabled)

    def load_markets(self):
        self.loaded = True

    def fetch_balance(self):
        self.balance_calls += 1
        return {"free": {"USDT": 100}}


def test_connect_sandbox_enables_sandbox_before_authentication(monkeypatch):
    service = ExchangeService()
    clients = []

    def factory(config):
        client = FakeClient(config)
        clients.append(client)
        return client

    monkeypatch.setattr(service, "_exchange_class", staticmethod(lambda name: ("binance", factory)))

    result = service.connect("u1", "binance", "API_KEY", "API_SECRET", sandbox=True)

    client = clients[0]
    assert client.sandbox_calls == [True]
    assert client.loaded is True
    assert client.balance_calls == 1
    assert result["sandbox"] is True


def test_connect_live_does_not_enable_sandbox(monkeypatch):
    service = ExchangeService()
    clients = []

    def factory(config):
        client = FakeClient(config)
        clients.append(client)
        return client

    monkeypatch.setattr(service, "_exchange_class", staticmethod(lambda name: ("binance", factory)))

    result = service.connect("u1", "binance", "API_KEY", "API_SECRET", sandbox=False)

    assert clients[0].sandbox_calls == []
    assert result["sandbox"] is False
