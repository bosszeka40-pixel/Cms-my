import os
import unittest

from backend.security.execution_gateway import cancel_real_order, submit_real_order


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

    def test_live_requires_explicit_gate(self):
        os.environ["TRADING_MODE"] = "live"
        os.environ["LIVE_TRADING_GATE"] = "true"
        self.assertEqual(submit_real_order(lambda value: value, "ok"), "ok")
