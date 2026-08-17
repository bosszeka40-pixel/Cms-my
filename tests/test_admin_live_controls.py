"""Regression coverage for authenticated administrative LIVE controls."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException

from backend.admin import (
    LiveTogglePayload,
    live_control_audit,
    live_controls,
    set_ai_bot_live_control,
    set_bot_live_control,
    set_global_live_control,
)
from backend.security.live_controls import LIVE_CONTROL_STATE, LiveControlState


class AdminLiveControlContractTests(unittest.TestCase):
    """Keep the API contract explicit without contacting an exchange."""

    def test_state_defaults_to_global_kill_switch_enabled(self):
        state = LiveControlState()
        self.assertTrue(state.global_kill_switch)
        self.assertEqual(state.bot_live, {})
        self.assertEqual(state.ai_bot_live, {})

    def test_bot_and_ai_bot_toggles_are_independent_and_audited(self):
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
        state.set_ai_bot_live("ai-2", enabled=False, actor="admin")

        self.assertTrue(state.bot_live["bot-1"])
        self.assertTrue(state.ai_bot_live["ai-1"])
        self.assertFalse(state.ai_bot_live["ai-2"])
        self.assertEqual(len(state.audit_log), 4)
        self.assertTrue(all(entry["actor"] == "admin" for entry in state.audit_log))

    def test_kill_switch_blocks_enabled_bot(self):
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        self.assertFalse(state.global_kill_switch)

    def test_authenticated_admin_endpoints_mutate_global_and_individual_controls(self):
        request = SimpleNamespace(session={"user_email": "admin@example.com"})
        admin = SimpleNamespace(email="admin@example.com", role="admin")
        with patch("backend.admin.engine.get_user", return_value=admin):
            before = LIVE_CONTROL_STATE.snapshot()
            try:
                set_global_live_control(LiveTogglePayload(enabled=False), request)
                set_bot_live_control("bot-endpoint", LiveTogglePayload(enabled=True), request)
                set_ai_bot_live_control("ai-endpoint", LiveTogglePayload(enabled=True), request)
                snapshot = live_controls(request)
                self.assertFalse(snapshot["global_kill_switch"])
                self.assertTrue(snapshot["bot_live"]["bot-endpoint"])
                self.assertTrue(snapshot["ai_bot_live"]["ai-endpoint"])
                self.assertEqual(len(live_control_audit(request)["entries"]), len(before["audit_log"]) + 3)
            finally:
                LIVE_CONTROL_STATE.global_kill_switch = before["global_kill_switch"]
                LIVE_CONTROL_STATE.bot_live = before["bot_live"]
                LIVE_CONTROL_STATE.ai_bot_live = before["ai_bot_live"]
                LIVE_CONTROL_STATE.audit_log = before["audit_log"]

    def test_live_control_endpoints_require_admin_session(self):
        request = SimpleNamespace(session={})
        with self.assertRaises(HTTPException) as exc:
            live_controls(request)
        self.assertEqual(exc.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
