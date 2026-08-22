"""Unified execution gate combining live mode and risk checks."""

from dataclasses import dataclass

from .live_guard import live_guard_check
from .live_trading_guard import LiveTradingGuard
from .risk_management import RiskManager


@dataclass
class ExecutionDecision:
    allowed: bool
    reason: str
    position_fraction: float = 0.0


class TradingExecutionGate:
    """Single entry point before any real trade execution."""

    def __init__(self):
        self.live_guard = LiveTradingGuard()
        self.risk_manager = RiskManager()

    def check(self, balance: float, leverage: float, order_notional: float = None,
              stop_loss_pct: float = 0.02, notional: float = None) -> ExecutionDecision:
        if order_notional is None:
            order_notional = notional or 0.0

        safety = live_guard_check(risk_score=stop_loss_pct)
        if not safety.allowed:
            return ExecutionDecision(False, safety.reason)

        if not self.live_guard.allow_order(order_notional):
            return ExecutionDecision(False, "Live trading guard blocked order.")

        risk = self.risk_manager.decide(balance, leverage, stop_loss_pct)
        if not risk.allowed:
            return ExecutionDecision(False, risk.reason)

        return ExecutionDecision(True, "Order passed all safety checks.", risk.position_fraction)

    def status(self) -> dict:
        return {
            "live_guard": self.live_guard.status(),
            "risk_manager": self.risk_manager.status(),
        }
