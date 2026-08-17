"""Global fail-closed guard for CCXT private execution methods.

The application has several places that construct CCXT clients. This module
wraps supported exchange constructors at package import time so authenticated
clients cannot bypass the central execution gateway, even when a caller uses
CCXT directly instead of ExchangeService.
"""
from __future__ import annotations

from functools import wraps
from types import MethodType
from typing import Any

import ccxt

from .security.execution_gateway import cancel_real_order, submit_real_order

SUPPORTED_EXCHANGES = (
    "binance",
    "bybit",
    "kraken",
    "okx",
    "bitfinex",
    "pionex",
)

_INSTALLED = False


def _wrap_client(client: Any) -> Any:
    original_create = getattr(client, "create_order", None)
    if callable(original_create) and not getattr(original_create, "_cms_guarded", False):
        @wraps(original_create)
        def guarded_create(self, *args: Any, **kwargs: Any):
            return submit_real_order(original_create, *args, **kwargs)
        guarded_create._cms_guarded = True
        client.create_order = MethodType(guarded_create, client)

    original_cancel = getattr(client, "cancel_order", None)
    if callable(original_cancel) and not getattr(original_cancel, "_cms_guarded", False):
        @wraps(original_cancel)
        def guarded_cancel(self, *args: Any, **kwargs: Any):
            return cancel_real_order(original_cancel, *args, **kwargs)
        guarded_cancel._cms_guarded = True
        client.cancel_order = MethodType(guarded_cancel, client)

    return client


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    for name in SUPPORTED_EXCHANGES:
        exchange_class = getattr(ccxt, name, None)
        if exchange_class is None or getattr(exchange_class, "_cms_guarded_factory", False):
            continue

        @wraps(exchange_class)
        def guarded_factory(config=None, _exchange_class=exchange_class, **kwargs):
            merged = dict(config or {})
            merged.update(kwargs)
            return _wrap_client(_exchange_class(merged))

        guarded_factory._cms_guarded_factory = True
        setattr(ccxt, name, guarded_factory)
    _INSTALLED = True


install()
