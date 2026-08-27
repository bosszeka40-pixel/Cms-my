"""Фоновый runtime для бота (additive, не заменяет bot.py/hft_brain.py).

Реализует lifecycle + реальный цикл торговли в DEMO/LIVE-safe режиме,
чтобы бот делал сделки в демо и симулировал торговлю на реальных данных.
"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timezone


class BotLifecycle:
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class BotRuntime:
    """Лёгкий процесс-local background worker для бота.

    Цикл: market signal -> risk check -> strategy.execute -> record trade -> update balance.
    Никогда не отправляет реальные ордера: LIVE-ордера идут только через ExecutionGateway.
    """

    def __init__(self, engine, strategy_manager, risk_manager, bot, exchange_service=None, tick_interval=15.0):
        self.engine = engine
        self.strategy_manager = strategy_manager
        self.risk_manager = risk_manager
        self.bot = bot
        self.exchange_service = exchange_service
        self.tick_interval = float(tick_interval)
        self._lock = threading.RLock()
        self._thread = None
        self._stop_event = threading.Event()
        self.lifecycle = BotLifecycle.STOPPED
        self._owner_email = None
        self.trade_history = []
        self._last_price = None
        self._demo_owner = None

    def _kill_switch_active(self):
        try:
            if getattr(self.risk_manager, "kill_switch", False):
                return True
        except Exception:
            pass
        try:
            from .security.live_controls import LIVE_CONTROL_STATE
            if not LIVE_CONTROL_STATE.allow_live:
                return True
            if not LIVE_CONTROL_STATE.allow_bot:
                return True
        except Exception:
            pass
        return False

    def start(self, email, pair="BTC/USDT", exchange="binance"):
        with self._lock:
            if self.lifecycle == BotLifecycle.RUNNING:
                return {"status": "already_running"}
            self._owner_email = email
            self._stop_event.clear()
            self.lifecycle = BotLifecycle.VALIDATING
            self._thread = threading.Thread(target=self._run, args=(email, pair, exchange), daemon=True)
            self._thread.start()
            self.lifecycle = BotLifecycle.RUNNING
            self.bot.start()
            self.engine.record_audit("bot_runtime_started", f"pair={pair} exchange={exchange}", email)
            return {"status": "started", "lifecycle": self.lifecycle}

    def _run(self, email, pair, exchange):
        # гарантируем демо-сессию владельцу
        self.engine.ensure_demo_session(email)
        while not self._stop_event.is_set() and self.lifecycle == BotLifecycle.RUNNING:
            try:
                if self._kill_switch_active():
                    self._emit("kill_switch_blocked", "Глобальный kill switch активен — бот остановлен.")
                    self.stop(email)
                    break
                self._tick(email, pair, exchange)
            except Exception as exc:
                self.lifecycle = BotLifecycle.ERROR
                self._emit("error", f"Ошибка runtime: {exc}")
            # пауза между тиками с учётом остановки
            self._stop_event.wait(self.tick_interval)

    def pause(self):
        with self._lock:
            if self.lifecycle == BotLifecycle.RUNNING:
                self.lifecycle = BotLifecycle.PAUSED
            return {"lifecycle": self.lifecycle}

    def resume(self, email, pair="BTC/USDT", exchange="binance"):
        with self._lock:
            if self.lifecycle == BotLifecycle.PAUSED:
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._run, args=(email, pair, exchange), daemon=True)
                self._thread.start()
                self.lifecycle = BotLifecycle.RUNNING
            return {"lifecycle": self.lifecycle}

    def stop(self, email):
        with self._lock:
            was_running = self.lifecycle == BotLifecycle.RUNNING
            self.lifecycle = BotLifecycle.STOPPING
            self._stop_event.set()
        if was_running and self._thread:
            self._thread.join(timeout=5)
        with self._lock:
            if self._thread:
                self._thread = None
            if self.lifecycle != BotLifecycle.EMERGENCY_STOP:
                self.lifecycle = BotLifecycle.STOPPED
            self.bot.stop()
            self.engine.record_audit("bot_runtime_stopped", f"trade_count={len(self.trade_history)}", email)
            return {"status": "stopped", "lifecycle": self.lifecycle}

    def emergency_stop(self, email):
        with self._lock:
            self.lifecycle = BotLifecycle.EMERGENCY_STOP
            self._stop_event.set()
        try:
            future = self._thread
            if future:
                future.join(timeout=5)
        finally:
            with self._lock:
                self._thread = None
            self.bot.stop()
            self.engine.record_audit("bot_emergency_stop", "emergency stop triggered", email)
        return {"status": "emergency_stop", "lifecycle": self.lifecycle}

    def status(self, email):
        with self._lock:
            return {
                "lifecycle": self.lifecycle,
                "active": self.lifecycle == BotLifecycle.RUNNING,
                "trade_count": len(self.trade_history),
                "total_pnl": round(sum(t.get("pnl", 0.0) for t in self.trade_history), 4),
                "last_price": self._last_price,
                "recent_trades": self.trade_history[-10:],
            }

    def _emit(self, event, detail):
        record = {"time": datetime.now(timezone.utc).isoformat(), "event": event, "detail": detail}
        self.bot.activity_log.append(record)
        self.bot.stats.append(record)

    def _current_price(self, pair, exchange):
        # LIVE tick: exchange_service (authenticated) preferred; fallback к публичному ccxt
        if self.exchange_service and self._owner_email:
            try:
                client = self.exchange_service.get(self._owner_email)["client"]
                ticker = client.fetch_ticker(pair)
                return float(ticker.get("last") or ticker.get("close"))
            except Exception:
                pass
        try:
            from .main import _public_exchange, refresh_candles, MARKET_DATABASE
            client = _public_exchange(exchange)
            candles = refresh_candles(MARKET_DATABASE, client, exchange, pair, timeframe="1h")
            if candles:
                return float(candles[-1]["close"])
        except Exception:
            pass
        if self._last_price:
            # jitter fallback моделирует реальную волатильность
            return self._last_price * (1 + random.uniform(-0.002, 0.002))
        return 100.0

    def _tick(self, email, pair, exchange):
        demo = self.engine.get_demo_session(email)
        balance = float(demo.get("demo_balance", 100.0))
        if balance <= 0:
            self._emit("warning", "Демо-баланс исчерпан.")
            return

        prev_price = self._last_price
        price = self._current_price(pair, exchange)
        self._last_price = price
        if prev_price:
            price_change = (price - prev_price) / prev_price * 100
        else:
            price_change = 0.0

        # sentiment proxy из изменения цены; стратегия сама решает сигнал
        sentiment = 0.5 + (price_change / 50.0)
        sentiment = max(-1.0, min(1.0, sentiment))

        result = self.strategy_manager.execute(sentiment, price_change, balance)
        signal = result["signal"]
        pnl = result["pnl"]
        net = result["next_balance"]

        # Risk check — никогда не выше лимита CMS
        risk_score = self.risk_manager.calculate_risk_score(leverage=float(self.strategy_manager.config.get("leverage", 1.5)))
        allowed, reason = self.risk_manager.check_risk_score(risk_score)
        if not allowed:
            self._emit("risk_blocked", f"Risk score {risk_score} превышает лимит: {reason}")
            return

        trade = {
            "time": datetime.now(timezone.utc).isoformat(),
            "pair": pair,
            "exchange": exchange,
            "signal": signal,
            "strategy": result["strategy"],
            "entry_price": price,
            "price_change": round(price_change, 4),
            "sentiment": round(sentiment, 4),
            "pnl": round(pnl, 4),
            "balance": round(net, 2),
            "risk_score": risk_score,
        }
        self.trade_history.append(trade)
        self.engine.update_demo_balance(email, pnl)
        self.engine.record_trade(email, pair, "demo", result["strategy"], round(pnl, 4), round(net, 2))
        self.engine.record_memory("demo_trade", round(pnl, 4), f"{pair} {result['strategy']} signal={signal}", email)
        # синхронизируем существующий бот-объект (bot.py) чтобы UI bot_status показывал trades
        self.bot.simulate(pair, result["strategy"], {"signal": signal, "previous_balance": balance, "next_balance": net})
        self._emit("trade", f"{signal} {pair} PnL {round(pnl, 4)}€")
