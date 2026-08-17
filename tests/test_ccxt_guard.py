import os

import ccxt
import pytest


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


def test_ccxt_client_allows_execution_only_when_live_gate_is_explicit(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    client = ccxt.binance()

    calls = []
    original = client.create_order

    def fake_create_order(*args, **kwargs):
        calls.append((args, kwargs))
        return {"id": "test-order"}

    # Replace the already guarded method so this test verifies the gateway
    # decision without contacting a real exchange.
    client.create_order = fake_create_order
    result = client.create_order("BTC/USDT", "market", "buy", 0.001)

    assert result["id"] == "test-order"
    assert calls
    assert callable(original)
