import pytest

from backend.security.execution_policy import assert_real_order_allowed


def test_demo_blocks_real_execution(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "demo")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(PermissionError):
        assert_real_order_allowed()


def test_shadow_blocks_real_execution(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "shadow")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(PermissionError):
        assert_real_order_allowed()


def test_backtest_blocks_real_execution(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "backtest")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(PermissionError):
        assert_real_order_allowed()


def test_live_requires_explicit_gate(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(PermissionError):
        assert_real_order_allowed()


def test_live_policy_allows_only_explicit_live_gate(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    assert_real_order_allowed()


def test_invalid_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "unexpected")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    with pytest.raises(PermissionError):
        assert_real_order_allowed()
