"""Safe AI shadow-trading orchestration.

This module deliberately has no exchange order-placement capability. It accepts
market observations, asks the existing strategy layer for a decision, records
an auditable shadow decision, and can feed the existing learning memory.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


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

    def evaluate(self, *, user_email: str, pair: str, price: float,
                 news_sentiment: float = 0.0, price_change: float = 0.0,
                 balance: float) -> dict[str, Any]:
        if price <= 0 or balance <= 0:
            raise ValueError("Цена и баланс должны быть положительными.")

        strategy = self.strategy_manager.execute(
            news_sentiment, price_change, balance
        )
        signal = str(strategy.get("signal", "WAIT")).upper()
        side = "buy" if "BUY" in signal else "sell" if "SELL" in signal else "wait"
        confidence = 0.0 if side == "wait" else min(1.0, max(0.0, abs(float(price_change)) * 10.0))

        risk = self.risk_manager.decide(balance, 1.0)
        allowed = bool(risk.allowed) and side != "wait"
        reason = str(risk.reason) if not risk.allowed else "Strategy signal passed shadow risk gate."

        decision_id = datetime.now(timezone.utc).strftime("shadow-%Y%m%d%H%M%S%f")
        decision = ShadowDecision(
            decision_id=decision_id,
            pair=pair,
            side=side if allowed else "blocked",
            confidence=confidence,
            strategy=strategy["strategy"],
            mode=self.MODE,
            reason=reason,
            entry_price=float(price) if allowed else None,
            stop_loss=None,
            take_profit=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self.engine.record_bot_stat(
            "ai_shadow_decision", str(asdict(decision))
        )
        self.engine.record_audit(
            "ai_shadow_decision", str(asdict(decision)), user_email
        )
        self.engine.record_memory(
            "ai_shadow_decision",
            float(strategy.get("pnl", 0.0)),
            f"pair={pair}; side={decision.side}; confidence={confidence:.4f}; decision={decision_id}",
            user_email,
        )
        return {"allowed": allowed, "risk_reason": reason, **asdict(decision)}
