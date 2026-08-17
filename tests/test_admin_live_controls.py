"""Regression coverage for authenticated administrative LIVE controls."""

import unittest
from unittest.mock import Mock, patch

from backend.security.live_controls import LiveControlState


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


if __name__ == "__main__":
    unittest.main()
