"""Minimal CCXT-compatible adapter for the Pionex REST API.

The stock CCXT library (any version) does not ship a ``pionex`` class
(upstream request ccxt/ccxt#18847 remains open), so the project cannot rely
on CCXT for this exchange.  This module implements the small subset of the
unified CCXT interface that this codebase actually uses, talking to
``https://api.pionex.com`` directly:

  public (no credentials)
    * fetch_ohlcv(symbol, timeframe=, since=, limit=) -> ccxt-style OHLCV
    * fetch_ticker(symbol)
    * load_markets() / .markets / .fees
  private (HMAC-SHA256, ``PIONEX-KEY`` / ``PIONEX-SIGNATURE`` headers)
    * fetch_balance()
    * create_order(symbol, order_type, side, amount, price=, params=)
    * cancel_order(order_id, symbol=, params=)
    * amount_to_precision(symbol, amount)

Auth (per official openapi.yaml):
  - ``timestamp`` (ms) is always part of the query string, ±20s valid.
  - GET:    signature = METHOD + "/path?" + sorted(query incl timestamp)
  - POST/DELETE: order params go into the JSON body (all values as strings),
    signature = METHOD + "/path?timestamp=..." + body
  - result is hex HMAC-SHA256 of the payload using the API secret, sent as
    ``PIONEX-SIGNATURE``.  Responses use the envelope
    ``{result, timestamp, data?|code?, message?}``.

All real order execution still flows through
``backend.security.execution_gateway`` (fail-closed), exactly as for the
CCXT-backed exchanges.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import threading
import time
from collections.abc import Mapping
from typing import Any

import requests

logger = logging.getLogger("cms.pionex")

BASE_URL = "https://api.pionex.com"

TIMEFRAMES: dict[str, str] = {
    "1m": "1M",
    "5m": "5M",
    "15m": "15M",
    "30m": "30M",
    "1h": "60M",
    "4h": "4H",
    "8h": "8H",
    "12h": "12H",
    "1d": "1D",
}

FEE_TAKER = 0.0005
FEE_MAKER = 0.0005


class PionexError(RuntimeError):
    """Raised on Pionex API-level failures (result=false or network errors)."""


def _sorted_query(params: Mapping[str, Any]) -> str:
    """Build 'a=1&b=2' from params, keys sorted; values NOT url-encoded
    (per official signing instructions, encoding happens only on the URL)."""
    return "&".join(f"{k}={v}" for k, v in sorted(params.items()))


def _urlencode(params: Mapping[str, Any]) -> str:
    from urllib.parse import urlencode

    return urlencode({str(k): str(v) for k, v in params.items()})


class PionexClient:
    """CCXT-like client for Pionex REST (public market data + signed private API)."""

    id = "pionex"
    name = "Pionex"
    has: dict[str, bool] = {
        "fetchOHLCV": True,
        "fetchTicker": True,
        "fetchBalance": True,
        "createOrder": True,
        "cancelOrder": True,
        "fetchTradingFee": False,
    }

    def __init__(self, params: Mapping[str, Any] | None = None):
        params = dict(params or {})
        self.apiKey: str | None = str(params.get("apiKey") or "").strip() or None
        self.secret: str | None = str(params.get("secret") or "").strip() or None
        self.timeout: float = float(params.get("timeout", 15 * 1000)) / 1000.0
        self._rate_limit = float(params.get("enableRateLimit", False)) > 0
        self._min_interval = 0.12
        self._lock = threading.Lock()
        self._last_request = 0.0
        self.markets: dict[str, dict[str, Any]] = {}
        self.markets_by_id: dict[str, dict[str, Any]] = {}
        self.fees: dict[str, Any] = {
            "trading": {
                "taker": FEE_TAKER,
                "maker": FEE_MAKER,
                "percentage": True,
            }
        }
        self.timeframes = dict(TIMEFRAMES)
        self._sandbox = False

    # ------------------------------------------------------------------ util
    def set_sandbox_mode(self, enabled: bool) -> None:
        # Pionex REST has no separate sandbox environment in this spec.
        self._sandbox = bool(enabled)

    def _throttle(self) -> None:
        with self._lock:
            delay = self._min_interval - (time.monotonic() - self._last_request)
            if delay > 0 and self._rate_limit:
                time.sleep(delay)
            self._last_request = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        signed: bool = False,
    ) -> dict[str, Any]:
        self._throttle()
        params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        url = f"{BASE_URL}/{path}"
        headers: dict[str, str] = {}

        if signed:
            if not self.apiKey or not self.secret:
                raise ValueError("Pionex private API requires apiKey and secret.")
            params = dict(params)
            params["timestamp"] = int(time.time() * 1000)
            if method in ("POST", "DELETE"):
                # order params go to the JSON body (as strings), only timestamp
                # participates in the query string / signature prefix.
                body_params = {k: v for k, v in params.items() if k != "timestamp"}
                query_string = _sorted_query({"timestamp": params["timestamp"]})
                payload = f"{method}/{path}?{query_string}"
                body = _json_string(body_params)
                if body_params:
                    payload += body
                endpoint = f"{url}?{query_string}"
                response = requests.request(
                    method, endpoint, data=body, headers=_signed_headers(payload, self.apiKey, self.secret, content_type=True), timeout=self.timeout
                )
            else:
                query_string = _sorted_query(params)
                payload = f"{method}/{path}?{query_string}"
                endpoint = f"{url}?{_urlencode(params)}"
                response = requests.request(
                    method, endpoint, headers=_signed_headers(payload, self.apiKey, self.secret), timeout=self.timeout
                )
        else:
            if params:
                endpoint = f"{url}?{_urlencode(params)}"
            else:
                endpoint = url
            response = requests.request(method, endpoint, timeout=self.timeout)

        try:
            data = response.json()
        except ValueError:
            raise PionexError(f"Pionex {method} {path}: invalid JSON ({response.status_code}).")
        if not isinstance(data, dict):
            raise PionexError(f"Pionex {method} {path}: unexpected response shape.")
        if data.get("result") is False:
            raise PionexError(
                "Pionex {} {}: code={} message={}".format(
                    method, path, data.get("code"), data.get("message")
                )
            )
        return data

    # ------------------------------------------------------------------ public
    def _require_market(self, symbol: str) -> dict[str, Any]:
        if not self.markets:
            self.load_markets()
        market = self.markets.get(symbol)
        if not market:
            raise ValueError(f"Торговая пара {symbol} недоступна на Pionex.")
        return market

    def load_markets(self, *args: Any, **kwargs: Any) -> dict[str, dict[str, Any]]:
        if self.markets:
            return self.markets
        payload = self._request("GET", "api/v1/common/symbols", {"type": "SPOT"})
        symbols = ((payload.get("data") or {}).get("symbols")) or []
        self.markets = {}
        self.markets_by_id = {}
        for item in symbols:
            mid = str(item.get("symbol") or "")
            if "_" not in mid:
                continue
            base, _, quote = mid.lower().partition("_")
            symbol = f"{base.upper()}/{quote.upper()}"
            limits = {
                "amount": {
                    "min": _num(item.get("sizeMin") or item.get("minTradeSize")),
                    "max": _num(item.get("sizeMax") or item.get("maxTradeSize")),
                },
                "price": {"min": _num(item.get("priceMin") or item.get("minPrice"))},
                "cost": {"min": _num(item.get("amountMin") or item.get("minOrderAmount"))},
            }
            trading = True
            market = {
                "id": mid,
                "symbol": symbol,
                "base": base.upper(),
                "quote": quote.upper(),
                "active": trading,
                "taker": FEE_TAKER,
                "maker": FEE_MAKER,
                "limits": limits,
                "precision": {
                    "amount": _num(item.get("sizePrecision") or item.get("quantityPrecision")),
                    "price": _num(item.get("pricePrecision") or item.get("tickSize")),
                },
            }
            self.markets[symbol] = market
            self.markets_by_id[mid] = market
        if not self.markets:
            raise PionexError("Pionex /common/symbols вернул пустой список.")
        return self.markets

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1m", since: int | None = None, limit: int | None = None) -> list[list[float]]:
        """Return ccxt-style OHLCV ``[[ts, open, high, low, close, volume], ...]``.

        The public klines endpoint caps ``limit`` at 500 records; when ``since``
        is passed and the server rejects ``startTime``, a single retry without
        ``startTime`` (most recent candles) is performed.
        """
        market = self._require_market(symbol)
        interval = TIMEFRAMES.get((timeframe or "1m").lower(), "1M")
        params: dict[str, Any] = {"symbol": market["id"], "interval": interval}
        if limit:
            params["limit"] = int(min(int(limit), 500))
        if since:
            params["startTime"] = int(since)

        try:
            payload = self._request("GET", "api/v1/market/klines", params)
        except PionexError:
            if "startTime" not in params:
                raise
            retry = dict(params)
            retry.pop("startTime", None)
            payload = self._request("GET", "api/v1/market/klines", retry)

        klines = ((payload.get("data") or {}).get("klines")) or []
        result: list[list[float]] = []
        for k in klines:
            open_ = _num(k.get("open"))
            high = _num(k.get("high"))
            low = _num(k.get("low"))
            close = _num(k.get("close"))
            volume = _num(k.get("volume"))
            timestamp = _num(k.get("time"))
            if open_ is None or timestamp is None:
                continue
            result.append([float(timestamp), float(open_ or 0.0), float(high or open_ or 0.0), float(low or open_ or 0.0), float(close or open_ or 0.0), float(volume or 0.0)])
        result.sort(key=lambda row: row[0])
        return result

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        market = self._require_market(symbol)
        payload = self._request("GET", "api/v1/market/tickers", {"symbol": market["id"]})
        tickers = ((payload.get("data") or {}).get("tickers")) or []
        ticker = next((t for t in tickers if str(t.get("symbol")) == market["id"]), None)
        if ticker is None and tickers:
            ticker = tickers[0]
        if ticker is None:
            raise PionexError(f"Pionex ticker {symbol} не найден.")
        ts = _num(ticker.get("time")) or _num(ticker.get("timestamp"))
        open_ = _num(ticker.get("open"))
        close = _num(ticker.get("close"))
        last = close if close is not None else _num(ticker.get("last"))
        return {
            "symbol": symbol,
            "timestamp": float(ts or 0.0),
            "datetime": None,
            "open": float(open_ or 0.0) if open_ is not None else None,
            "high": float(_num(ticker.get("high")) or 0.0) if _num(ticker.get("high")) is not None else None,
            "low": float(_num(ticker.get("low")) or 0.0) if _num(ticker.get("low")) is not None else None,
            "last": float(last) if last is not None else None,
            "close": float(last) if last is not None else None,
            "baseVolume": float(_num(ticker.get("volume")) or 0.0) if _num(ticker.get("volume")) is not None else None,
            "info": ticker,
        }

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        market = self._require_market(symbol)
        precision = (market.get("precision") or {}).get("amount")
        if precision is not None and precision > 0:
            decimals = int(precision) if precision >= 1 else int(round(-_log10(precision)))
            return float(round(amount, max(0, min(8, decimals))))
        return float(round(amount, 8))

    # ------------------------------------------------------------------ private
    def fetch_balance(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = self._request("GET", "api/v1/account/balances", params or {}, signed=True)
        balances = ((payload.get("data") or {}).get("balances")) or []
        free, used, total = {}, {}, {}
        for item in balances:
            code = str(item.get("coin") or "").upper()
            if not code:
                continue
            free[code] = float(_num(item.get("free")) or 0.0)
            used[code] = float(_num(item.get("frozen")) or 0.0)
            total[code] = free[code] + used[code]
        return {"info": payload, "free": free, "used": used, "total": total, "timestamp": None}

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        market = self._require_market(symbol)
        order_type = (order_type or "").lower()
        side = (side or "").lower()
        if order_type not in {"market", "limit"} or side not in {"buy", "sell"}:
            raise ValueError("Pionex adapter поддерживает только market/limit и buy/sell.")
        params = dict(params or {})
        body: dict[str, Any] = {
            "symbol": market["id"],
            "side": side.upper(),
            "type": order_type.upper(),
        }
        if order_type == "limit":
            if price is None or price <= 0:
                raise ValueError("Для лимитного ордера нужна положительная цена.")
            body["size"] = _fmt(amount)
            body["price"] = _fmt(float(price))
        else:
            if side == "sell":
                body["size"] = _fmt(amount)
            else:
                # Pionex MARKET buy uses the quote-currency order amount.
                cost = amount * price if price else amount
                body["amount"] = _fmt(cost)
        if params.get("clientOrderId"):
            body["clientOrderId"] = str(params["clientOrderId"])[:64]
        payload = self._request("POST", "api/v1/trade/order", body, signed=True)
        order = payload.get("data") or {}
        return self._parse_order(order, market)

    def cancel_order(self, order_id: str | int, symbol: str | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        market = self._require_market(symbol) if symbol else None
        if not market:
            raise ValueError("Pionex cancel_order требует symbol.")
        body: dict[str, Any] = {"symbol": market["id"], "orderId": int(order_id)}
        payload = self._request("DELETE", "api/v1/trade/order", body, signed=True)
        return self._parse_order(payload.get("data") or {}, market)

    def _parse_order(self, order: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": order.get("orderId"),
            "symbol": market.get("symbol"),
            "side": str(order.get("side") or "").lower(),
            "type": str(order.get("type") or "").lower(),
            "price": _num(order.get("price")),
            "amount": _num(order.get("size")),
            "filled": _num(order.get("filledSize")),
            "cost": _num(order.get("filledAmount")),
            "status": str(order.get("status") or "").lower(),
            "info": order,
        }


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _fmt(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _log10(value: float) -> float:
    import math

    return math.log10(float(value))


def _json_string(params: dict[str, Any]) -> str:
    import json

    return json.dumps(params, separators=(",", ":"), ensure_ascii=True)


def _signed_headers(payload: str, api_key: str, secret: str, content_type: bool = False) -> dict[str, str]:
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    headers = {"PIONEX-KEY": api_key, "PIONEX-SIGNATURE": signature}
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers