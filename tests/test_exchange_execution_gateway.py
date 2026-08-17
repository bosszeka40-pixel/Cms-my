import os
import unittest

from backend.security.execution_gateway import cancel_real_order, submit_real_order
from backend.security.live_controls import LiveControlState


class ExchangeExecutionGatewayTests(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.get("TRADING_MODE")
        self._gate = os.environ.get("LIVE_TRADING_GATE")

    def tearDown(self):
        if self._mode is None:
            os.environ.pop("TRADING_MODE", None)
        else:
            os.environ["TRADING_MODE"] = self._mode
        if self._gate is None:
            os.environ.pop("LIVE_TRADING_GATE", None)
        else:
            os.environ["LIVE_TRADING_GATE"] = self._gate

    def test_demo_blocks_order_submission(self):
        os.environ["TRADING_MODE"] = "demo"
        os.environ["LIVE_TRADING_GATE"] = "false"
        with self.assertRaises(PermissionError):
            submit_real_order(lambda: "executed")

    def test_shadow_blocks_order_cancellation(self):
        os.environ["TRADING_MODE"] = "shadow"
        os.environ["LIVE_TRADING_GATE"] = "false"
        with self.assertRaises(PermissionError):
            cancel_real_order(lambda: "cancelled")

    def test_live_requires_explicit_admin_state(self):
        os.environ["TRADING_MODE"] = "live"
        os.environ["LIVE_TRADING_GATE"] = "true"
        with self.assertRaises(PermissionError):
            submit_real_order(lambda value: value, "ok")

    def test_live_reaches_executor_with_explicit_admin_state(self):
        os.environ["TRADING_MODE"] = "live"
        os.environ["LIVE_TRADING_GATE"] = "true"
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        self.assertEqual(
            submit_real_order(
                lambda value: value,
                "ok",
                live_state=state,
                bot_id="bot-1",
            ),
            "ok",
        )


if __name__ == "__main__":
    unittest.main()
