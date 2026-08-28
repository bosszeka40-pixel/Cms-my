import os
import math
from threading import Lock

import ccxt

from .security.execution_gateway import cancel_real_order, submit_real_order
from .security.execution_policy import current_mode, real_execution_allowed
from .security.live_controls import LIVE_CONTROL_STATE, LiveControlState


SUPPORTED_EXCHANGES = {"binance", "bybit", "kraken", "okx", "bitfinex", "pionex"}


class ExchangeService:
    """Keeps authenticated CCXT clients in memory; API secrets are never persisted."""

    def __init__(self, live_state: LiveControlState | None = None):
        self._clients = {}
        self._lock = Lock()
        self._live_state = live_state or LIVE_CONTROL_STATE

    @staticmethod
    def _exchange_class(name):
        exchange_name = (name or "").strip().lower()
        if exchange_name not in SUPPORTED_EXCHANGES:
            raise ValueError("Неизвестная или неподдерживаемая биржа.")
        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            raise ValueError("Биржа недоступна в установленной версии CCXT.")
        return exchange_name, exchange_class

    def connect(self, user_id, name, api_key, api_secret, passphrase=None, sandbox=False):
        if not user_id or not isinstance(api_key, str) or not isinstance(api_secret, str):
            raise ValueError("API key и API secret обязательны.")
        api_key = api_key.strip()
        api_secret = api_secret.strip()
        if not api_key or not api_secret:
            raise ValueError("API key и API secret обязательны.")
        exchange_name, exchange_class = self._exchange_class(name)
        client = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "password": passphrase or None,
            "enableRateLimit": True,
            "timeout": 15000,
        })
        if sandbox:
            client.set_sandbox_mode(True)
        client.load_markets()
        client.fetch_balance()
        with self._lock:
            self._clients[user_id] = {
                "name": exchange_name,
                "client": client,
                "sandbox": bool(sandbox),
                "api_key_hint": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****",
            }
        return self.status(user_id)

    def get(self, user_id):
        with self._lock:
            connection = self._clients.get(user_id)
        if not connection:
            raise LookupError("Биржа не подключена.")
        return connection

    def status(self, user_id):
        connection = self.get(user_id) if user_id in self._clients else None
        mode = current_mode().value
        return {
            "connected": bool(connection),
            "exchange": connection["name"] if connection else None,
            "sandbox": connection["sandbox"] if connection else None,
            "api_key": connection["api_key_hint"] if connection else None,
            "trading_mode": mode,
            "live_trading_enabled": real_execution_allowed(),
        }

    def list_connected(self, user_id):
        """Возвращает подключённые биржи пользователя для UI."""
        with self._lock:
            conns = list(self._clients.values())
        return [{"name": c["name"], "sandbox": c["sandbox"], "api_key_hint": c["api_key_hint"]} for c in conns]

    def disconnect(self, user_id):
        with self._lock:
            self._clients.pop(user_id, None)

    def balance(self, user_id):
        return self.get(user_id)["client"].fetch_balance()

    def ticker(self, user_id, symbol):
        return self.get(user_id)["client"].fetch_ticker(symbol)

    def trading_fee(self, user_id, symbol):
        client = self.get(user_id)["client"]
        try:
            fee = client.fetch_trading_fee(symbol)
            rate = fee.get("taker") or fee.get("rate")
            if rate is not None and math.isfinite(float(rate)):
                return float(rate)
        except (AttributeError, ccxt.BaseError):
            pass
        market = client.markets.get(symbol) or {}
        rate = market.get("taker")
        if rate is None:
            rate = (client.fees.get("trading") or {}).get("taker")
        if rate is None:
            rate = float(os.getenv("SIMULATION_FEE_RATE", "0.001"))
        return float(rate)

    def minimum_order_amount(self, user_id, symbol, price=None):
        connection = self.get(user_id)
        market = connection["client"].markets.get(symbol)
        if not market:
            raise ValueError("Торговая пара недоступна на подключенной бирже.")
        amount_min = ((market.get("limits") or {}).get("amount") or {}).get("min")
        cost_min = ((market.get("limits") or {}).get("cost") or {}).get("min")
        if cost_min and price and price > 0:
            amount_min = max(amount_min or 0, cost_min / price)
        if not amount_min or amount_min <= 0:
            raise ValueError("Биржа не сообщила минимальный размер ордера.")
        return float(connection["client"].amount_to_precision(symbol, amount_min))

    def create_order(
        self, user_id, symbol, order_type, side, amount, price=None, params=None,
        *, bot_id=None, ai_bot_id=None, live_state=None,
    ):
        connection = self.get(user_id)
        client = connection["client"]
        order_type = (order_type or "").lower()
        side = (side or "").lower()
        if not symbol or order_type not in {"market", "limit"} or side not in {"buy", "sell"}:
            raise ValueError("Допустимы только market/limit и buy/sell.")
        if not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
            raise ValueError("Количество должно быть положительным числом.")
        if symbol not in client.markets:
            raise ValueError("Торговая пара недоступна на подключенной бирже.")
        minimum_price = price if price is not None else client.fetch_ticker(symbol).get("last")
        minimum_amount = self.minimum_order_amount(user_id, symbol, minimum_price)
        if amount < minimum_amount:
            raise ValueError(f"Минимальное количество для {symbol}: {minimum_amount}.")
        gateway_kwargs = {
            "live_state": live_state or self._live_state,
            "bot_id": bot_id,
            "ai_bot_id": ai_bot_id,
        }
        if order_type == "market":
            return submit_real_order(
                client.create_order, symbol, order_type, side, amount, None, params or {}, **gateway_kwargs
            )
        if price is None or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError("Для лимитного ордера нужна положительная цена.")
        return submit_real_order(
            client.create_order, symbol, order_type, side, amount, price, params or {}, **gateway_kwargs
        )

    def cancel_order(
        self, user_id, order_id, symbol, params=None, *, bot_id=None, ai_bot_id=None, live_state=None
    ):
        client = self.get(user_id)["client"]
        return cancel_real_order(
            client.cancel_order, order_id, symbol, params or {},
            live_state=live_state or self._live_state,
            bot_id=bot_id,
            ai_bot_id=ai_bot_id,
        )
