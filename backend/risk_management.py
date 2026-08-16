from dataclasses import dataclass
import math


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    position_fraction: float


class RiskManager:
    """Small, deterministic risk gate shared by paper and live execution."""

    def __init__(self, risk_per_trade: float = 0.01, daily_loss_limit: float = 0.03,
                 max_drawdown: float = 0.15, max_leverage: float = 2.0):
        self.risk_per_trade = risk_per_trade
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown = max_drawdown
        self.max_leverage = max_leverage
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.kill_switch = False

    def decide(self, balance: float, leverage: float, stop_loss_pct: float = 0.02) -> RiskDecision:
        if self.kill_switch:
            return RiskDecision(False, "Аварийный выключатель активен.", 0.0)
        if not math.isfinite(balance) or balance <= 0:
            return RiskDecision(False, "Баланс должен быть положительным.", 0.0)
        if not math.isfinite(leverage) or leverage <= 0 or leverage > self.max_leverage:
            return RiskDecision(False, "Плечо должно быть конечным и не превышать установленный лимит.", 0.0)
        if not math.isfinite(self.daily_pnl):
            return RiskDecision(False, "Состояние дневного PnL повреждено.", 0.0)
        if self.daily_pnl <= -balance * self.daily_loss_limit:
            return RiskDecision(False, "Достигнут дневной лимит убытка.", 0.0)
        if self.peak_balance and balance <= self.peak_balance * (1 - self.max_drawdown):
            return RiskDecision(False, "Достигнута максимальная просадка.", 0.0)
        if not math.isfinite(stop_loss_pct) or stop_loss_pct <= 0:
            return RiskDecision(False, "Stop-loss должен быть положительным.", 0.0)
        if not math.isfinite(self.risk_per_trade) or self.risk_per_trade <= 0:
            return RiskDecision(False, "Риск на сделку должен быть положительным.", 0.0)
        fraction = min(1.0, self.risk_per_trade / stop_loss_pct)
        return RiskDecision(True, "Риск в пределах лимитов.", fraction)

    def record(self, pnl: float, balance: float) -> None:
        if not math.isfinite(pnl) or not math.isfinite(balance) or balance <= 0:
            return
        self.daily_pnl += float(pnl)
        self.peak_balance = max(self.peak_balance, float(balance))

    def reset_daily(self) -> None:
        self.daily_pnl = 0.0

    def set_kill_switch(self, enabled: bool) -> None:
        self.kill_switch = bool(enabled)

    def status(self) -> dict:
        return {
            "kill_switch": self.kill_switch,
            "daily_pnl": round(self.daily_pnl, 8),
            "peak_balance": round(self.peak_balance, 8),
            "risk_per_trade": self.risk_per_trade,
            "daily_loss_limit": self.daily_loss_limit,
            "max_drawdown": self.max_drawdown,
            "max_leverage": self.max_leverage,
        }
