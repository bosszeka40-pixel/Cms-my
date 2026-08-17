"""Safe AI shadow-trading orchestration.

Shadow mode never places an exchange order. It records a virtual position only
after strategy, AI confidence and risk validation. Virtual P/L is calculated
only when a later market price is supplied to settle that position.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import math

from .cms_core import Trade

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
    trade_id: int | None = None


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
        trade_id = None
        if allowed:
            user = self.engine.get_user(user_email)
            if not user:
                raise ValueError("Пользователь Shadow не найден.")
            session = self.engine.SessionLocal()
            try:
                trade = Trade(
                    user_id=user.id,
                    pair=pair,
                    mode="ai_shadow_open",
                    strategy=f"{strategy['strategy']}|side={side}|entry={price:.12g}|decision={decision_id}",
                    pnl=0.0,
                    balance=float(balance),
                )
                session.add(trade)
                session.commit()
                session.refresh(trade)
                trade_id = trade.id
            finally:
                session.close()

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
            trade_id=trade_id,
        )
        payload = asdict(decision)

        self.engine.record_bot_stat("ai_shadow_decision", str(payload))
        self.engine.record_audit("ai_shadow_decision", str(payload), user_email)
        self.engine.record_memory(
            "ai_shadow_decision",
            0.0,
            f"pair={pair}; side={decision.side}; confidence={ai_confidence:.4f}; decision={decision_id}; trade_id={trade_id}; status=unsettled",
            user_email,
        )
        return {
            "allowed": allowed,
            "risk_reason": reason,
            "risk_position_fraction": risk.position_fraction if allowed else 0.0,
            "settlement_status": "unsettled" if trade_id else "not_opened",
            **payload,
        }

    def settle(self, *, user_email: str, trade_id: int, exit_price: float) -> dict[str, Any]:
        if not math.isfinite(float(exit_price)) or exit_price <= 0:
            raise ValueError("Цена выхода должна быть положительным конечным числом.")
        user = self.engine.get_user(user_email)
        if not user:
            raise ValueError("Пользователь Shadow не найден.")
        session = self.engine.SessionLocal()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id, Trade.user_id == user.id).first()
            if not trade:
                raise ValueError("Shadow trade не найден.")
            if trade.mode != "ai_shadow_open":
                raise ValueError("Shadow trade уже закрыта.")
            parts = dict(item.split("=", 1) for item in trade.strategy.split("|")[1:] if "=" in item)
            entry = float(parts["entry"])
            side = parts["side"]
            pnl_pct = ((exit_price - entry) / entry) if side == "buy" else ((entry - exit_price) / entry)
            pnl = float(trade.balance) * pnl_pct
            trade.pnl = pnl
            trade.mode = "ai_shadow_settled"
            session.commit()
            result = {
                "trade_id": trade.id,
                "pair": trade.pair,
                "side": side,
                "entry_price": entry,
                "exit_price": float(exit_price),
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "status": "settled",
            }
        finally:
            session.close()

        self.engine.record_bot_stat("ai_shadow_settlement", str(result))
        self.engine.record_audit("ai_shadow_settlement", str(result), user_email)
        self.engine.record_memory(
            "ai_shadow_trade_result",
            result["pnl"],
            f"trade_id={trade_id}; pair={result['pair']}; side={result['side']}; entry={entry}; exit={exit_price}; pnl_pct={pnl_pct:.8f}",
            user_email,
        )
        return result
