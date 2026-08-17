import ccxt
import pytest

from backend.security.execution_gateway import submit_real_order


def test_ccxt_client_blocks_create_order_by_default(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "demo")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    client = ccxt.binance()

    with pytest.raises(PermissionError):
        client.create_order("BTC/USDT", "market", "buy", 0.001)


def test_ccxt_client_blocks_cancel_order_by_default(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "shadow")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    client = ccxt.binance()

    with pytest.raises(PermissionError):
        client.cancel_order("test-order", "BTC/USDT")


def test_gateway_allows_executor_only_when_live_gate_is_explicit(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")

    calls = []

    def fake_executor(*args, **kwargs):
        calls.append((args, kwargs))
        return {"id": "test-order"}

    result = submit_real_order(fake_executor, "BTC/USDT", "market", "buy", 0.001)

    assert result == {"id": "test-order"}
    assert calls
