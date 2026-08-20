"""Central execution-mode policy.

The policy is intentionally conservative: Demo/Shadow/Backtest can never
request real exchange execution. LIVE requires an explicit application mode
and a separate gate flag; the gate is not enabled by default.
"""
from __future__ import annotations

import os
from enum import Enum


class ExecutionMode(str, Enum):
    BACKTEST = "backtest"
    DEMO = "demo"
    SHADOW = "shadow"
    LIVE = "live"


class ExecutionPolicyError(RuntimeError):
    pass


def current_mode() -> ExecutionMode:
    raw = os.getenv("TRADING_MODE", ExecutionMode.DEMO.value).strip().lower()
    try:
        return ExecutionMode(raw)
    except ValueError as exc:
        raise ExecutionPolicyError(f"Invalid TRADING_MODE: {raw!r}") from exc


def live_gate_enabled() -> bool:
    return os.getenv("LIVE_TRADING_GATE", "false").strip().lower() == "true"


def require_shadow_mode() -> ExecutionMode:
    mode = current_mode()
    if mode == ExecutionMode.LIVE:
        raise ExecutionPolicyError("Shadow operation is disabled while TRADING_MODE=live.")
    return mode


def require_real_execution() -> None:
    if current_mode() is not ExecutionMode.LIVE:
        raise ExecutionPolicyError("Real exchange execution is disabled outside TRADING_MODE=live.")
    if not live_gate_enabled():
        raise ExecutionPolicyError("LIVE trading gate is not enabled.")


def assert_shadow_only() -> None:
    """Fail closed if a shadow component is ever loaded in LIVE mode."""
    require_shadow_mode()
