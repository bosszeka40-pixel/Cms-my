import os
import unittest
from unittest.mock import patch

from backend.security.execution_policy import (
    TradingMode,
    assert_real_execution_allowed,
    assert_virtual_mode,
    current_mode,
    real_execution_allowed,
)


class ExecutionPolicyTests(unittest.TestCase):
    def test_defaults_to_demo(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(current_mode(), TradingMode.DEMO)
            self.assertFalse(real_execution_allowed())

    def test_unknown_mode_fails_closed_to_demo(self):
        with patch.dict(os.environ, {"TRADING_MODE": "something-unknown"}, clear=True):
            self.assertIs(current_mode(), TradingMode.DEMO)
            self.assertFalse(real_execution_allowed())

    def test_live_requires_independent_gate(self):
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "false"}, clear=True):
            self.assertFalse(real_execution_allowed())
            with self.assertRaises(PermissionError):
                assert_real_execution_allowed()

    def test_live_requires_exact_gate(self):
        with patch.dict(os.environ, {"TRADING_MODE": "live", "LIVE_TRADING_GATE": "true"}, clear=True):
            self.assertTrue(real_execution_allowed())
            assert_real_execution_allowed()

    def test_virtual_modes_are_blocked_in_live(self):
        with patch.dict(os.environ, {"TRADING_MODE": "live"}, clear=True):
            with self.assertRaises(PermissionError):
                assert_virtual_mode()

    def test_virtual_modes_remain_available_outside_live(self):
        for mode in ("backtest", "demo", "shadow"):
            with self.subTest(mode=mode), patch.dict(os.environ, {"TRADING_MODE": mode}, clear=True):
                assert_virtual_mode()
                self.assertFalse(real_execution_allowed())


if __name__ == "__main__":
    unittest.main()
