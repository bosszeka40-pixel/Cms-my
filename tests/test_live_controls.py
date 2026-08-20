from backend.security.live_controls import LiveControlState, assert_live_controlled


def test_new_state_is_fail_closed():
    state = LiveControlState()
    assert not state.allows(bot_id="bot-1")


def test_global_kill_switch_blocks_enabled_bot():
    state = LiveControlState()
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    assert not state.allows(bot_id="bot-1")


def test_bot_can_be_enabled_after_global_switch_is_released():
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    assert state.allows(bot_id="bot-1")


def test_ai_bot_requires_its_own_switch():
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    assert not state.allows(bot_id="bot-1", ai_bot_id="ai-1")
    state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
    assert state.allows(bot_id="bot-1", ai_bot_id="ai-1")


def test_assertion_fails_closed():
    state = LiveControlState()
    try:
        assert_live_controlled(state, bot_id="bot-1")
    except PermissionError:
        pass
    else:
        raise AssertionError("disabled LIVE controls must reject execution")


def test_changes_are_audited():
    state = LiveControlState()
    state.set_global_kill_switch(enabled=False, actor="admin")
    state.set_bot_live("bot-1", enabled=True, actor="admin")
    assert [entry["kind"] for entry in state.audit_log] == [
        "global_kill_switch",
        "bot_live",
    ]
