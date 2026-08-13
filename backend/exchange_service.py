import os
import math
from threading import Lock

import ccxt


SUPPORTED_EXCHANGES = {"binance", "bybit", "kraken", "okx", "bitfinex", "pionex"}


class ExchangeService:
    """Keeps authenticated CCXT clients in memory; API secrets are never persisted."""

    def __init__(self):
        self._clients = {}
        self._lock = Lock()

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
        # Fetching the balance verifies authentication without exposing credentials.
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
        return {
            "connected": bool(connection),
            "exchange": connection["name"] if connection else None,
            "sandbox": connection["sandbox"] if connection else None,
            "api_key": connection["api_key_hint"] if connection else None,
            "live_trading_enabled": os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true",
        }

    def disconnect(self, user_id):
        with self._lock:
            self._clients.pop(user_id, None)

    def balance(self, user_id):
        connection = self.get(user_id)
        return connection["client"].fetch_balance()

    def ticker(self, user_id, symbol):
        connection = self.get(user_id)
        return connection["client"].fetch_ticker(symbol)

    def create_order(self, user_id, symbol, order_type, side, amount, price=None, params=None):
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
        if order_type == "market":
            return client.create_order(symbol, order_type, side, amount, None, params or {})
        if price is None or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError("Для лимитного ордера нужна положительная цена.")
        return client.create_order(symbol, order_type, side, amount, price, params or {})

    def cancel_order(self, user_id, order_id, symbol, params=None):
        connection = self.get(user_id)
        return connection["client"].cancel_order(order_id, symbol, params or {})
