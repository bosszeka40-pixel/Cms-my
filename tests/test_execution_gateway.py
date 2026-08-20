import os
import unittest
from unittest.mock import Mock, patch

from backend.security.execution_gateway import cancel_real_order, submit_real_order
from backend.security.live_controls import LiveControlState


class ExecutionGatewayTests(unittest.TestCase):
    def test_submit_is_blocked_by_default(self):
        executor = Mock(return_value={"ok": True})
        state = LiveControlState()
        with patch.dict(os.environ, {"TRADING_MODE": "demo", "LIVE_TRADING_GATE": "false"}, clear=False):
            with self.assertRaises(PermissionError):
                submit_real_order(executor, "BTC/USDT", 1.0, live_state=state, bot_id="bot-1")
        executor.assert_not_called()

    def test_cancel_is_blocked_in_shadow(self):
        executor = Mock(return_value={"ok": True})
        state = LiveControlState()
        with patch.dict(os.environ, {"TRADING_MODE": "shadow", "LIVE_TRADING_GATE": "true"}, clear=False):
            with self.assertRaises(PermissionError):
                cancel_real_order(executor, "order-1", live_state=state, bot_id="bot-1")
        executor.assert_not_called()

    def test_submit_reaches_executor_only_when_explicitly_live(self):
        executor = Mock(return_value={"id": "order-1"})
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "true"}, clear=False):
            result = submit_real_order(
                executor,
                "BTC/USDT",
                1.0,
                side="buy",
                live_state=state,
                bot_id="bot-1",
            )
        self.assertEqual(result, {"id": "order-1"})
        executor.assert_called_once_with("BTC/USDT", 1.0, side="buy")


if __name__ == "__main__":
    unittest.main()
