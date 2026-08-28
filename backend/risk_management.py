from dataclasses import dataclass
import math


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    position_fraction: float


class RiskManager:
    """Small, deterministic risk gate shared by paper and live execution."""

    MAX_RISK_SCORE = 60

    def __init__(self, risk_per_trade: float = 0.01, daily_loss_limit: float = 0.03,
                 max_drawdown: float = 0.15, max_leverage: float = 2.0):
        self.risk_per_trade = risk_per_trade
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown = max_drawdown
        self.max_leverage = max_leverage
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.kill_switch = False

    def calculate_risk_score(self, volatility: float = 0.02, leverage: float = 1.0,
                             drawdown: float = 0.0, liquidity: float = 0.8,
                             concentration: float = 0.1, positions: int = 1,
                             execution_complexity: int = 1, exchange_risk: float = 0.1,
                             slippage: float = 0.001, market_regime: str = "normal") -> int:
        """Calculate normalized risk score 0-100. Max allowed is 60."""
        score = 0.0
        score += min(20, volatility * 500)
        score += min(15, max(0, leverage - 1) * 15)
        score += min(15, drawdown * 100)
        score += min(10, max(0, 1 - liquidity) * 12)
        score += min(10, concentration * 50)
        score += min(5, positions * 1.5)
        score += min(5, execution_complexity * 2)
        score += min(5, exchange_risk * 25)
        score += min(5, slippage * 500)
        regime_mult = {"normal": 1.0, "volatile": 1.3, "trending": 0.9, "ranging": 1.1}.get(market_regime, 1.0)
        score *= regime_mult
        return max(0, min(100, int(score)))

    def check_risk_score(self, risk_score: int) -> tuple[bool, str]:
        """Check if risk_score is within allowed limit (0-60)."""
        if risk_score > self.MAX_RISK_SCORE:
            return False, f"Risk Score {risk_score} exceeds maximum {self.MAX_RISK_SCORE}. Strategy rejected."
        return True, "Risk Score within limits."

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
