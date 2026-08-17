"""Safe AI shadow-trading orchestration.

Shadow mode never places an exchange order. It records a decision only after
strategy and risk validation. Trade outcome is deliberately not written as P/L
until a later settlement step has an observed market outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import math


AI_CONFIDENCE_CUTOFF = 0.38


@dataclass
class ShadowDecision:
    decision_id: str
    pair: str
    side: str
    confidence: float
    strategy: str
    mode: str
    reason: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    created_at: str


class AIShadowTrader:
    """Paper-only coordinator for AI-assisted trading decisions."""

    MODE = "ai_shadow"

    def __init__(self, engine, strategy_manager, risk_manager, bot):
        self.engine = engine
        self.strategy_manager = strategy_manager
        self.risk_manager = risk_manager
        self.bot = bot

    def evaluate(
        self,
        *,
        user_email: str,
        pair: str,
        price: float,
        ai_confidence: float,
        news_sentiment: float = 0.0,
        price_change: float = 0.0,
        balance: float,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
    ) -> dict[str, Any]:
        values = (price, ai_confidence, balance, stop_loss_pct, take_profit_pct)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Параметры Shadow должны быть конечными числами.")
        if price <= 0 or balance <= 0:
            raise ValueError("Цена и баланс должны быть положительными.")
        if not 0.0 <= ai_confidence <= 1.0:
            raise ValueError("AI confidence должен находиться в диапазоне 0..1.")
        if stop_loss_pct <= 0 or take_profit_pct <= 0:
            raise ValueError("Stop-loss и take-profit должны быть положительными.")

        strategy = self.strategy_manager.execute(news_sentiment, price_change, balance)
        signal = str(strategy.get("signal", "WAIT")).upper()
        side = "buy" if "BUY" in signal else "sell" if "SELL" in signal else "wait"
        leverage = float(strategy.get("leverage", 1.0))

        risk = self.risk_manager.decide(balance, leverage, stop_loss_pct)
        allowed = bool(risk.allowed) and side != "wait" and ai_confidence >= AI_CONFIDENCE_CUTOFF

        if not risk.allowed:
            reason = str(risk.reason)
        elif side == "wait":
            reason = "Стратегия не дала торгового сигнала."
        elif ai_confidence < AI_CONFIDENCE_CUTOFF:
            reason = f"AI confidence ниже порога {AI_CONFIDENCE_CUTOFF:.2f}."
        else:
            reason = "AI confidence и стратегия прошли Shadow risk gate."

        stop_loss = None
        take_profit = None
        if allowed:
            if side == "buy":
                stop_loss = price * (1.0 - stop_loss_pct)
                take_profit = price * (1.0 + take_profit_pct)
            else:
                stop_loss = price * (1.0 + stop_loss_pct)
                take_profit = price * (1.0 - take_profit_pct)

        decision_id = datetime.now(timezone.utc).strftime("shadow-%Y%m%d%H%M%S%f")
        decision = ShadowDecision(
            decision_id=decision_id,
            pair=pair,
            side=side if allowed else "blocked",
            confidence=ai_confidence,
            strategy=strategy["strategy"],
            mode=self.MODE,
            reason=reason,
            entry_price=float(price) if allowed else None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        payload = asdict(decision)

        self.engine.record_bot_stat("ai_shadow_decision", str(payload))
        self.engine.record_audit("ai_shadow_decision", str(payload), user_email)
        # This is a decision event, not a settled trade. Do not teach the
        # learner a fabricated P/L value before the market outcome is known.
        self.engine.record_memory(
            "ai_shadow_decision",
            0.0,
            f"pair={pair}; side={decision.side}; confidence={ai_confidence:.4f}; decision={decision_id}; status=unsettled",
            user_email,
        )
        return {
            "allowed": allowed,
            "risk_reason": reason,
            "risk_position_fraction": risk.position_fraction if allowed else 0.0,
            "settlement_status": "unsettled",
            **payload,
        }
