"""Public market-data loop for AI Shadow Trading.

The feed uses CCXT public ticker data only. It never receives API keys and
never calls create_order/cancel_order/fetch_balance or any private exchange API.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import ccxt

from .ai_shadow import AIShadowTrader
from .cms_core import CMSEngine
from .bot import HFTBot
from .modules.strategy_manager import StrategyManager
from .risk_management import RiskManager


@dataclass
class FeedState:
    running: bool = False
    exchange: str = "binance"
    pair: str = "BTC/USDT"
    interval_seconds: float = 1.0
    last_price: float | None = None
    last_tick_at: float | None = None
    ticks: int = 0
    settlements: int = 0
    last_error: str | None = None


class AIShadowMarketFeed:
    """One-user, public-data ticker loop for Shadow position monitoring."""

    ALLOWED_EXCHANGES = {"binance", "bybit", "kraken", "okx", "bitfinex"}

    def __init__(self, engine: CMSEngine):
        self.engine = engine
        self.state = FeedState()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._user_email: str | None = None
        self._exchange_client: Any | None = None

    def _make_exchange(self, name: str):
        name = name.lower().strip()
        if name not in self.ALLOWED_EXCHANGES:
            raise ValueError("Неподдерживаемая публичная биржа.")
        exchange_class = getattr(ccxt, name, None)
        if exchange_class is None:
            raise ValueError("CCXT не поддерживает указанную биржу.")
        return exchange_class({"enableRateLimit": True})

    async def start(self, *, user_email: str, exchange: str, pair: str, interval_seconds: float = 1.0):
        if self._task and not self._task.done():
            raise ValueError("AI Shadow market feed уже запущен.")
        if not pair or "/" not in pair:
            raise ValueError("Укажите корректную торговую пару, например BTC/USDT.")
        if not 0.5 <= interval_seconds <= 60:
            raise ValueError("Интервал market feed должен быть от 0.5 до 60 секунд.")

        self._exchange_client = self._make_exchange(exchange)
        self._user_email = user_email
        self._stop = asyncio.Event()
        self.state = FeedState(
            running=True,
            exchange=exchange.lower(),
            pair=pair.upper(),
            interval_seconds=float(interval_seconds),
        )
        self._task = asyncio.create_task(self._run())
        return self.status()

    async def stop(self):
        self._stop.set()
        task = self._task
        if task and not task.done():
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except asyncio.TimeoutError:
                task.cancel()
        self._task = None
        self.state.running = False
        if self._exchange_client is not None:
            close = getattr(self._exchange_client, "close", None)
            if close:
                result = close()
                if asyncio.iscoroutine(result):
                    await result
        self._exchange_client = None
        return self.status()

    async def _run(self):
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                ticker = await asyncio.to_thread(
                    self._exchange_client.fetch_ticker, self.state.pair
                )
                price = float(ticker.get("last") or ticker.get("close") or 0)
                if price <= 0:
                    raise ValueError("Биржа не вернула положительную last/close цену.")
                self.state.last_price = price
                self.state.last_tick_at = time.time()
                self.state.ticks += 1
                trader = AIShadowTrader(
                    self.engine, StrategyManager(), RiskManager(), HFTBot()
                )
                results = trader.monitor(
                    user_email=self._user_email,
                    pair=self.state.pair,
                    market_price=price,
                )
                self.state.settlements += len(results)
                self.state.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.state.last_error = str(exc)

            elapsed = time.monotonic() - started
            await asyncio.wait_for(self._stop.wait(), timeout=max(0.05, self.state.interval_seconds - elapsed)) if not self._stop.is_set() else None

    def status(self) -> dict[str, Any]:
        return {
            "running": self.state.running,
            "exchange": self.state.exchange,
            "pair": self.state.pair,
            "interval_seconds": self.state.interval_seconds,
            "last_price": self.state.last_price,
            "last_tick_at": self.state.last_tick_at,
            "ticks": self.state.ticks,
            "settlements": self.state.settlements,
            "last_error": self.state.last_error,
            "execution": "shadow_only",
            "private_exchange_api": False,
        }
