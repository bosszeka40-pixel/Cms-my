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

    def __init__(self, engine, strategy_manager, risk_manager, bot, exchange_service=None, tick_interval=15.0, learner=None):
        self.engine = engine
        self.strategy_manager = strategy_manager
        self.risk_manager = risk_manager
        self.bot = bot
        self.exchange_service = exchange_service
        self.learner = learner
        self.tick_interval = float(tick_interval)
        self._lock = threading.RLock()
        self._thread = None
        self._stop_event = threading.Event()
        self.lifecycle = BotLifecycle.STOPPED
        self._owner_email = None
        self.trade_history = []
        self._last_price = None
        self._demo_owner = None
        self._last_context = None
        self._runtime_config = {
            "pair": "BTC/USDT",
            "exchange": "binance",
            "market_mode": "spot",
            "leverage": 1.0,
            "strategy": None,
            "bot_mode": "strategy",
        }
        self._last_market_info = None
        self._last_signal_hour = None

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

    def start(self, email, pair="BTC/USDT", exchange="binance", market_mode="spot",
              leverage=1.0, strategy=None, bot_mode="strategy"):
        with self._lock:
            if self.lifecycle == BotLifecycle.RUNNING:
                return {"status": "already_running", "lifecycle": self.lifecycle}
            self._owner_email = email
            self._runtime_config = {
                "pair": pair,
                "exchange": exchange,
                "market_mode": market_mode,
                "leverage": float(leverage or 1.0),
                "strategy": strategy,
                "bot_mode": bot_mode,
            }
            self._stop_event.clear()
            self.lifecycle = BotLifecycle.VALIDATING
            self._thread = threading.Thread(target=self._run, args=(email,), daemon=True)
            self._thread.start()
            self.lifecycle = BotLifecycle.RUNNING
            self.bot.start()
            self.engine.record_audit("bot_runtime_started", f"pair={pair} exchange={exchange} mode={market_mode} bot_mode={bot_mode}", email)
            return {"status": "started", "lifecycle": self.lifecycle}

    def _run(self, email):
        cfg = self._runtime_config
        # гарантируем демо-сессию владельцу
        self.engine.ensure_demo_session(email)
        while not self._stop_event.is_set() and self.lifecycle == BotLifecycle.RUNNING:
            try:
                if self._kill_switch_active():
                    self._emit("kill_switch_blocked", "Глобальный kill switch активен — бот остановлен.")
                    self.stop(email)
                    break
                self._tick(email, cfg.get("pair", "BTC/USDT"), cfg.get("exchange", "binance"))
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

    def resume(self, email, pair=None, exchange=None, market_mode=None,
               leverage=None, strategy=None, bot_mode=None):
        with self._lock:
            if self.lifecycle == BotLifecycle.PAUSED:
                cfg = dict(self._runtime_config)
                if pair:
                    cfg["pair"] = pair
                if exchange:
                    cfg["exchange"] = exchange
                if market_mode:
                    cfg["market_mode"] = market_mode
                if leverage is not None:
                    cfg["leverage"] = float(leverage or 1.0)
                if strategy is not None:
                    cfg["strategy"] = strategy
                if bot_mode:
                    cfg["bot_mode"] = bot_mode
                self._runtime_config = cfg
                self._owner_email = email
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._run, args=(email,), daemon=True)
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
            learning = getattr(self.learner, "stats", lambda: {})() if self.learner else None
            return {
                "lifecycle": self.lifecycle,
                "active": self.lifecycle == BotLifecycle.RUNNING,
                "trade_count": len(self.trade_history),
                "total_pnl": round(sum(t.get("pnl", 0.0) for t in self.trade_history), 4),
                "last_price": self._last_price,
                "recent_trades": self.trade_history[-10:],
                "learning_enabled": bool(self.learner and self.learner.enabled),
                "learning": learning,
                "context": (self._last_context or {}).get("candles") or None,
                "runtime": self._runtime_config,
                "market_info": self._last_market_info,
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

    def _market_context(self, pair, exchange):
        """Реальные фичи из стакана и графика: (candle_feat, depth_feat, vector)."""
        try:
            from .main import _public_exchange, refresh_candles, refresh_history, MARKET_DATABASE
            from .modules.order_book import fetch_order_book_snapshot, depth_features
            from .modules.market_features import candle_features, feature_vector
            client = _public_exchange(exchange)
            candles = refresh_candles(MARKET_DATABASE, client, exchange, pair, timeframe="1h")
            daily = refresh_history(MARKET_DATABASE, client, exchange, pair)
            snapshot = fetch_order_book_snapshot(client, pair, limit=20)
            candle_feat = candle_features(candles, daily)
            depth_feat = depth_features(snapshot)
            vector = feature_vector(candle_feat, depth_feat)
            context = {
                "pair": pair,
                "exchange": exchange,
                "candles": candle_feat,
                "depth": depth_feat,
                "vector": vector,
                "best_bid": snapshot.get("best_bid"),
                "best_ask": snapshot.get("best_ask"),
                "ts": snapshot.get("ts") or int(time.time() * 1000),
            }
            self._last_context = context
            return context
        except Exception:
            return self._last_context

    def _tick(self, email, pair, exchange):
        demo = self.engine.get_demo_session(email)
        balance = float(demo.get("demo_balance", 100.0))
        if balance <= 0:
            self._emit("warning", "Демо-баланс исчерпан.")
            return

        cfg = self._runtime_config
        market_mode = str(cfg.get("market_mode") or "spot")
        leverage = float(cfg.get("leverage") or 1.0)
        strategy = cfg.get("strategy")
        bot_mode = str(cfg.get("bot_mode") or "strategy")

        # 1) реальный контекст: цена, свечи, стакан
        context = self._market_context(pair, exchange)
        candle_feat = (context or {}).get("candles") or {}
        depth_feat = (context or {}).get("depth") or {}
        vector = (context or {}).get("vector")

        prev_price = self._last_price
        if candle_feat.get("last_price"):
            price = float(candle_feat["last_price"])
        else:
            price = self._current_price(pair, exchange)
        self._last_price = price
        if prev_price:
            price_change = (price - prev_price) / prev_price * 100
        else:
            price_change = candle_feat.get("momentum_1h", 0.0)
        # горизонт сигнала — часовой ход (движение, которое предсказывает сигнал)
        realized_move = float(candle_feat.get("momentum_1h") or price_change)

        # 2) рыночная информация бота: реальные данные выбранной биржи/пары/режима
        from .main import _exchange_fee_rate
        fee_rate = _exchange_fee_rate(exchange, pair, market_mode)
        self._last_market_info = {
            "pair": pair,
            "exchange": exchange,
            "market_mode": market_mode,
            "leverage": leverage,
            "last_price": price,
            "best_bid": (context or {}).get("best_bid"),
            "best_ask": (context or {}).get("best_ask"),
            "spread_pct": depth_feat.get("spread_pct"),
            "imbalance": depth_feat.get("imbalance"),
            "momentum_1h": candle_feat.get("momentum_1h"),
            "rsi14": candle_feat.get("rsi14"),
            "volume_ratio": candle_feat.get("volume_ratio"),
            "bid_depth_ratio": depth_feat.get("bid_depth_ratio"),
            "price_change_pct": round(price_change, 4),
            "fee_rate": fee_rate,
            "updated": datetime.now(timezone.utc).isoformat(),
        }

        # 3) сентимент из реальных фич (график + стакан)
        from .modules.market_features import heuristic_sentiment
        sentiment = heuristic_sentiment(candle_feat, depth_feat)
        ai_confidence = None
        ai_direction = 0

        # 4) ИИ-слой: если включён и уверен — задаёт направление
        if self.learner and self.learner.enabled and vector:
            ai_confidence = self.learner.predict_confidence(vector)
            ai_direction = self.learner.suggest_direction(ai_confidence)
            if ai_direction != 0:
                sentiment = ai_direction * max(0.3, abs(sentiment))
            if abs(sentiment) < 0.05 and candle_feat.get("momentum_1h", 0.0) == 0.0 and not depth_feat:
                sentiment = 0.0

        # 5) Risk check — никогда не выше лимита CMS (по выбранному плечу)
        risk_score = self.risk_manager.calculate_risk_score(leverage=leverage)
        allowed, reason = self.risk_manager.check_risk_score(risk_score)
        if not allowed:
            self._emit("risk_blocked", f"Risk score {risk_score} превышает лимит: {reason}")
            return

        if bot_mode == "full_auto":
            # один сигнал в час: не дублировать одну и ту же часовую сделку каждые 15 секунд
            hour_key = time.strftime("%Y-%m-%d-%H", time.gmtime())
            if getattr(self, "_last_signal_hour", None) == hour_key:
                self._emit("skip", f"{pair} {exchange} bot=автономный · сигнал этого часа уже закрыт (cooldown)")
                return
            # бот самостоятельно: сам решает когда действовать, сам оценивает результат
            result = self._autonomous_tick(sentiment, realized_move, balance, leverage, fee_rate)
            if result["signal"] in ("KEEP", "FLAT", "HOLD"):
                self._emit("skip", f"{pair} {exchange} bot=автономный · sentiment={round(sentiment, 4)} — бездействие (низкая уверенность)")
                return
            self._last_signal_hour = hour_key
        else:
            result = self.strategy_manager.execute(
                sentiment, price_change, balance, fee_rate=fee_rate, leverage=leverage, strategy=strategy
            )

        signal = result["signal"]
        pnl = result["pnl"]
        net = result["next_balance"]

        # 6) обучение по факту сделки (реальные свечи+стакан -> исход)
        if self.learner and vector is not None:
            self.learner.update(vector, pnl if prev_price else 0.0)

        trade = {
            "time": datetime.now(timezone.utc).isoformat(),
            "pair": pair,
            "exchange": exchange,
            "market_mode": market_mode,
            "leverage": leverage,
            "bot_mode": bot_mode,
            "signal": signal,
            "strategy": result["strategy"],
            "entry_price": price,
            "price_change": round(price_change, 4),
            "realized_move": round(realized_move, 4),
            "sentiment": round(sentiment, 4),
            "pnl": round(pnl, 4),
            "balance": round(net, 2),
            "risk_score": risk_score,
            "ai_confidence": round(ai_confidence, 4) if ai_confidence is not None else None,
            "ai_direction": ai_direction,
            "learner_trained": bool(self.learner and vector is not None),
            "features": {
                "momentum_1h": candle_feat.get("momentum_1h"),
                "rsi14": candle_feat.get("rsi14"),
                "imbalance": depth_feat.get("imbalance"),
                "spread_pct": depth_feat.get("spread_pct"),
                "bid_depth_ratio": depth_feat.get("bid_depth_ratio"),
            },
        }
        self.trade_history.append(trade)
        self.engine.update_demo_balance(email, pnl)
        self.engine.record_trade(email, pair, "demo", result["strategy"], round(pnl, 4), round(net, 2))
        self.engine.record_memory("demo_trade", round(pnl, 4), f"{pair} {result['strategy']} signal={signal}", email)
        # синхронизируем существующий бот-объект (bot.py) чтобы UI bot_status показывал trades
        self.bot.simulate(pair, result["strategy"], {"signal": signal, "previous_balance": balance, "next_balance": net})
        self._emit("trade", f"{signal} {pair} {market_mode} PnL {round(pnl, 4)}€")

    def _autonomous_tick(self, sentiment, price_change, balance, leverage, fee_rate):
        """Автономный режим: бот без стратегии сам решает действовать или нет."""
        threshold = 0.10
        if sentiment >= threshold:
            direction = 1
        elif sentiment <= -threshold:
            direction = -1
        else:
            direction = 0
        if direction == 0:
            return {"signal": "KEEP", "pnl": 0.0, "next_balance": balance,
                    "strategy": "autonomous", "leverage": leverage, "fee_rate": fee_rate, "fee": 0.0}
        capture = 0.5 + 0.5 * min(1.0, abs(sentiment))
        move_pct = (price_change or 0.0) * direction * capture * leverage
        fee = balance * leverage * fee_rate * 2
        next_balance = max(0.0, balance * (1.0 + move_pct / 100.0) - fee)
        return {
            "signal": "BUY" if direction > 0 else "SELL",
            "pnl": next_balance - balance,
            "next_balance": next_balance,
            "strategy": "autonomous",
            "leverage": leverage,
            "fee_rate": fee_rate,
            "fee": fee,
        }
