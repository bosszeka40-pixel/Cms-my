"""Safety guard for live trading execution.

Keeps live orders disabled by default until explicitly enabled by deployment config.
"""

import os


class LiveTradingGuard:
    def __init__(self):
        self.enabled = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
        self.max_order_notional = float(os.getenv("MAX_ORDER_NOTIONAL", "1000"))

    def allow_order(self, notional: float) -> bool:
        if not self.enabled:
            return False
        if not isinstance(notional, (int, float)):
            return False
        if notional <= 0:
            return False
        return notional <= self.max_order_notional

    allowed = allow_order

    def status(self) -> dict:
        return {
            "live_trading_enabled": self.enabled,
            "max_order_notional": self.max_order_notional,
        }
