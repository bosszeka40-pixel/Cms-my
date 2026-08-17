"""Central execution policy for trading modes.

This module is deliberately dependency-light so every execution path can use the
same fail-closed rules. LIVE execution requires two independent gates.
"""
from __future__ import annotations

import os
from enum import Enum


class TradingMode(str, Enum):
    BACKTEST = "backtest"
    DEMO = "demo"
    SHADOW = "shadow"
    LIVE = "live"


def current_mode() -> TradingMode:
    raw = os.getenv("TRADING_MODE", TradingMode.DEMO.value).strip().lower()
    try:
        return TradingMode(raw)
    except ValueError:
        return TradingMode.DEMO


def live_gate_enabled() -> bool:
    return os.getenv("LIVE_TRADING_GATE", "false").strip().lower() in {"1", "true", "yes", "on"}


def live_execution_allowed() -> bool:
    return current_mode() is TradingMode.LIVE and live_gate_enabled()


def real_order_allowed() -> bool:
    """Fail-closed decision for real exchange order submission."""
    return live_execution_allowed()


def virtual_execution_allowed() -> bool:
    return current_mode() in {TradingMode.DEMO, TradingMode.SHADOW, TradingMode.BACKTEST}


def assert_real_order_allowed() -> None:
    if not real_order_allowed():
        raise PermissionError("Real exchange execution is disabled by the trading execution policy.")
