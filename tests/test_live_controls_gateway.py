"""Regression tests for the administrative LIVE execution boundary."""

import pytest

from backend.security.execution_gateway import submit_real_order
from backend.security.live_controls import LiveControlState


def test_gateway_fails_closed_without_admin_state(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    with pytest.raises(PermissionError):
        submit_real_order(lambda: "sent", bot_id="bot-1")


def test_gateway_denies_with_global_kill_switch(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    state = LiveControlState()
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    with pytest.raises(PermissionError):
        submit_real_order(lambda: "sent", live_state=state, bot_id="bot-1")


def test_gateway_allows_enabled_bot_without_calling_real_exchange(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    assert submit_real_order(lambda: "test-double", live_state=state, bot_id="bot-1") == "test-double"


def test_gateway_denies_ai_bot_until_its_switch_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    with pytest.raises(PermissionError):
        submit_real_order(
            lambda: "sent",
            live_state=state,
            bot_id="bot-1",
            ai_bot_id="ai-1",
        )


def test_gateway_allows_enabled_ai_bot_with_test_double(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_TRADING_GATE", "true")
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
    assert submit_real_order(
        lambda: "test-double",
        live_state=state,
        bot_id="bot-1",
        ai_bot_id="ai-1",
    ) == "test-double"
