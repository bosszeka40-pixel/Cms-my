"""Single choke point for exchange execution.

All private order submission/cancellation code should pass through this module.
The gateway is intentionally tiny and fail-closed so callers cannot accidentally
invent a second execution policy.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from .execution_policy import assert_real_execution_allowed

T = TypeVar("T")


def submit_real_order(executor: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Submit a real exchange order only when the central LIVE gate allows it."""
    assert_real_execution_allowed()
    return executor(*args, **kwargs)


def cancel_real_order(executor: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Cancel a real exchange order only when the central LIVE gate allows it."""
    assert_real_execution_allowed()
    return executor(*args, **kwargs)
