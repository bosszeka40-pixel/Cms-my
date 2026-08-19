"""Central execution policy for trading modes.

The policy is deliberately fail-closed: real exchange execution is allowed only
when the application is explicitly in LIVE mode and the independent live gate is
enabled. DEMO/SHADOW/BACKTEST never authorize private order execution.
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
    return os.getenv("LIVE_TRADING_GATE", "false").strip().lower() == "true"


def real_execution_allowed() -> bool:
    return current_mode() is TradingMode.LIVE and live_gate_enabled()


def assert_real_execution_allowed() -> None:
    if not real_execution_allowed():
        raise PermissionError(
            "Real exchange execution is disabled. "
            "Set TRADING_MODE=live and LIVE_TRADING_GATE=true explicitly."
        )


def assert_virtual_mode() -> None:
    if current_mode() is TradingMode.LIVE:
        raise PermissionError("Virtual execution is disabled while TRADING_MODE=live.")
