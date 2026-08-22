import os

from backend.live_trading_guard import LiveTradingGuard
from backend.risk_management import RiskManager
from backend.trading_execution_gate import TradingExecutionGate


def test_strategy_risk_live_guard_bot_flow_blocks_live_by_default(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "1000")

    risk = RiskManager()
    live_guard = LiveTradingGuard()
    gate = TradingExecutionGate(risk_manager=risk, live_guard=live_guard)

    decision = gate.check_order(
        balance=1000,
        leverage=1,
        stop_loss_pct=0.02,
        notional=100,
    )

    assert decision.allowed is False


def test_strategy_risk_live_guard_flow_allows_safe_paper_execution(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "1000")

    risk = RiskManager()
    live_guard = LiveTradingGuard()
    gate = TradingExecutionGate(risk_manager=risk, live_guard=live_guard)

    decision = gate.check_order(
        balance=1000,
        leverage=1,
        stop_loss_pct=0.02,
        notional=100,
    )

    assert decision.allowed is True
