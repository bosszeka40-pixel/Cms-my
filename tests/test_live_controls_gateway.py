"""Regression tests for the administrative LIVE control boundary."""

import pytest

from backend.security.live_controls import LiveControlState, assert_live_controlled


def test_fresh_state_denies_live() -> None:
    state = LiveControlState()
    with pytest.raises(PermissionError):
        assert_live_controlled(state, bot_id="bot-1")


def test_bot_requires_global_kill_switch_off() -> None:
    state = LiveControlState()
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    with pytest.raises(PermissionError):
        assert_live_controlled(state, bot_id="bot-1")


def test_bot_can_be_enabled_after_global_switch_off() -> None:
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    assert_live_controlled(state, bot_id="bot-1")


def test_ai_bot_requires_its_own_switch() -> None:
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    with pytest.raises(PermissionError):
        assert_live_controlled(state, bot_id="bot-1", ai_bot_id="ai-1")


def test_ai_bot_can_be_enabled_independently() -> None:
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
    assert_live_controlled(state, bot_id="bot-1", ai_bot_id="ai-1")


def test_audit_log_records_each_control_change() -> None:
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
    assert len(state.audit_log) == 3
    assert {entry["actor"] for entry in state.audit_log} == {"admin"}
