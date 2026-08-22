import os
import unittest

from backend.live_trading_guard import LiveTradingGuard


class TestLiveTradingGuard(unittest.TestCase):
    def test_blocks_live_when_disabled(self):
        old = os.environ.get("LIVE_TRADING_ENABLED")
        os.environ["LIVE_TRADING_ENABLED"] = "false"
        try:
            guard = LiveTradingGuard()
            self.assertFalse(guard.allowed(10))
        finally:
            if old is None:
                os.environ.pop("LIVE_TRADING_ENABLED", None)
            else:
                os.environ["LIVE_TRADING_ENABLED"] = old

    def test_blocks_large_orders(self):
        os.environ["LIVE_TRADING_ENABLED"] = "true"
        os.environ["MAX_ORDER_NOTIONAL"] = "100"
        guard = LiveTradingGuard()
        self.assertFalse(guard.allowed(101))


if __name__ == "__main__":
    unittest.main()
