import os
import unittest
from unittest.mock import Mock, patch

from backend.security.execution_gateway import submit_real_order
from backend.security.live_controls import LiveControlState


class ExecutionGatewayLiveControlTests(unittest.TestCase):
    def test_live_requires_explicit_admin_state(self):
        executor = Mock(return_value={"id": "order-1"})
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "true"}, clear=False):
            with self.assertRaises(PermissionError):
                submit_real_order(executor, "BTC/USDT", 1.0, bot_id="bot-1")
        executor.assert_not_called()

    def test_bot_live_requires_global_switch_off(self):
        state = LiveControlState()
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        executor = Mock(return_value={"id": "order-1"})
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "true"}, clear=False):
            with self.assertRaises(PermissionError):
                submit_real_order(executor, "BTC/USDT", 1.0, live_state=state, bot_id="bot-1")
        executor.assert_not_called()

    def test_ai_bot_live_is_independent(self):
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        executor = Mock(return_value={"id": "order-1"})
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "true"}, clear=False):
            with self.assertRaises(PermissionError):
                submit_real_order(
                    executor,
                    "BTC/USDT",
                    1.0,
                    live_state=state,
                    bot_id="bot-1",
                    ai_bot_id="ai-1",
                )
        executor.assert_not_called()

    def test_fully_enabled_controls_reach_executor(self):
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
        executor = Mock(return_value={"id": "order-1"})
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "true"}, clear=False):
            result = submit_real_order(
                executor,
                "BTC/USDT",
                1.0,
                live_state=state,
                bot_id="bot-1",
                ai_bot_id="ai-1",
            )
        self.assertEqual(result, {"id": "order-1"})
        executor.assert_called_once_with("BTC/USDT", 1.0)


if __name__ == "__main__":
    unittest.main()
