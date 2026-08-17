import pytest

from backend.security.execution_policy import ExecutionBlocked, assert_real_order_allowed


def test_demo_blocks_real_execution(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "DEMO")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(ExecutionBlocked):
        assert_real_order_allowed()


def test_shadow_blocks_real_execution(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "SHADOW")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(ExecutionBlocked):
        assert_real_order_allowed()


def test_backtest_blocks_real_execution(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "BACKTEST")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(ExecutionBlocked):
        assert_real_order_allowed()


def test_live_requires_all_gates(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "LIVE")
    monkeypatch.setenv("LIVE_TRADING_GATE", "false")
    with pytest.raises(ExecutionBlocked):
        assert_real_order_allowed()


def test_live_policy_can_pass_only_when_gate_is_explicit(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "LIVE")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    assert_real_order_allowed()
