import pytest

from backend.security.execution_gateway import cancel_real_order, submit_real_order


def test_gateway_blocks_create_in_demo(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "demo")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")

    with pytest.raises(PermissionError):
        submit_real_order(lambda: {"id": "must-not-run"})


def test_gateway_blocks_cancel_in_shadow(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "shadow")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")

    with pytest.raises(PermissionError):
        cancel_real_order(lambda: {"id": "must-not-run"})


def test_gateway_allows_executor_only_with_explicit_live_gate(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    calls = []

    result = submit_real_order(lambda value: calls.append(value) or {"id": "test"}, 7)

    assert result == {"id": "test"}
    assert calls == [7]
