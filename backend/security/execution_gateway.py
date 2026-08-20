"""Single choke point for exchange execution.

All private order submission/cancellation code should pass through this module.
The gateway is intentionally tiny and fail-closed so callers cannot accidentally
invent a second execution policy.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from .execution_policy import assert_real_execution_allowed
from .live_controls import LiveControlState, assert_live_controlled

T = TypeVar("T")


def _assert_execution_allowed(
    *,
    live_state: LiveControlState | None,
    bot_id: str | None,
    ai_bot_id: str | None,
) -> None:
    """Apply both environment and administrative LIVE gates, fail-closed."""
    assert_real_execution_allowed()
    if live_state is None or not bot_id:
        raise PermissionError("LIVE trading requires an explicit administrative control")
    assert_live_controlled(live_state, bot_id=bot_id, ai_bot_id=ai_bot_id)


def submit_real_order(
    executor: Callable[..., T],
    *args: Any,
    live_state: LiveControlState | None = None,
    bot_id: str | None = None,
    ai_bot_id: str | None = None,
    **kwargs: Any,
) -> T:
    """Submit a real exchange order only when every LIVE gate allows it."""
    _assert_execution_allowed(
        live_state=live_state, bot_id=bot_id, ai_bot_id=ai_bot_id
    )
    return executor(*args, **kwargs)


def cancel_real_order(
    executor: Callable[..., T],
    *args: Any,
    live_state: LiveControlState | None = None,
    bot_id: str | None = None,
    ai_bot_id: str | None = None,
    **kwargs: Any,
) -> T:
    """Cancel a real exchange order only when every LIVE gate allows it."""
    _assert_execution_allowed(
        live_state=live_state, bot_id=bot_id, ai_bot_id=ai_bot_id
    )
    return executor(*args, **kwargs)
