"""Per-exchange metadata for the CMS trading platform.

Provides real (documented) fee schedules, supported market modes
(spot / isolated margin / cross margin / futures), and public REST
endpoints - including testnet/sandbox where available - so the admin
can verify real trading connectivity for every supported exchange.

Fees are the standard published tier-0 (VIP0) taker/maker rates in
decimal form. When CCXT market metadata carries an actual fee it wins;
these values are the fallback for the public catalog and for exchanges
that do not expose per-market fees (e.g. Pionex).
"""
from __future__ import annotations

from typing import Any

# Lower-case exchange id -> metadata. Order matches the alphabetical
# listing used by the UI (sorted(SUPPORTED_MARKET_EXCHANGES)).
EXCHANGE_CATALOG: dict[str, dict[str, Any]] = {
    "binance": {
        "name": "Binance",
        "fees": {
            "taker": 0.001,              # spot/margin 0.10%
            "maker": 0.001,
            "taker_margin": 0.001,
            "maker_margin": 0.001,
            "taker_futures": 0.0005,     # U-M futures 0.05%
            "maker_futures": 0.0002,
        },
        "features": {
            "spot": True,
            "margin_isolated": True,
            "margin_cross": True,
            "futures": True,
        },
        "max_leverage": {"spot": 1, "margin_isolated": 10, "margin_cross": 5, "futures": 125},
        "public": {"url": "https://api.binance.com", "ping": "/api/v3/ping"},
        "public_futures": {"url": "https://fapi.binance.com", "ping": "/fapi/v1/ping"},
        "testnet": {
            "spot": {"url": "https://testnet.binance.vision", "ping": "/api/v3/ping"},
            "futures": {"url": "https://testnet.binancefuture.com", "ping": "/fapi/v1/ping"},
            "note": "Требуются тестовые ключи: https://testnet.binance.vision",
        },
    },
    "bitfinex": {
        "name": "Bitfinex",
        "fees": {"taker": 0.002, "maker": 0.001},
        "features": {"spot": True, "margin_isolated": True, "margin_cross": True, "futures": True},
        "max_leverage": {"spot": 1, "margin_isolated": 3, "margin_cross": 10, "futures": 25},
        "public": {"url": "https://api-pub.bitfinex.com", "ping": "/v2/platform/status"},
        "testnet": {
            "spot": {"url": "https://api-test.bitfinex.com", "ping": "/v2/platform/status"},
            "note": "Sandbox, требуется ключ: https://thanos.bitfinex.com/",
        },
    },
    "bybit": {
        "name": "Bybit",
        "fees": {
            "taker": 0.001,              # spot 0.10%
            "maker": 0.001,
            "taker_futures": 0.00055,    # USDT perpetual 0.055%
            "maker_futures": 0.0002,
        },
        "features": {"spot": True, "margin_isolated": False, "margin_cross": True, "futures": True},
        "max_leverage": {"spot": 1, "margin_isolated": 1, "margin_cross": 10, "futures": 100},
        "public": {"url": "https://api.bybit.com", "ping": "/v5/market/time"},
        "testnet": {
            "spot": {"url": "https://api-testnet.bybit.com", "ping": "/v5/market/time"},
            "note": "Требуются тестовые ключи: https://testnet.bybit.com/",
        },
    },
    "kraken": {
        "name": "Kraken",
        "fees": {
            "taker": 0.0026,             # <$10k 30d volume: 0.26%
            "maker": 0.0016,
        },
        "features": {"spot": True, "margin_isolated": True, "margin_cross": True, "futures": False},
        "max_leverage": {"spot": 1, "margin_isolated": 5, "margin_cross": 5, "futures": 1},
        "public": {"url": "https://api.kraken.com", "ping": "/0/public/Time"},
        "testnet": {
            "spot": {"url": "https://api-sandbox.kraken.com", "ping": "/0/public/Time"},
            "note": "Ограниченный sandbox, требуется ключ.",
        },
    },
    "okx": {
        "name": "OKX",
        "fees": {
            "taker": 0.001,
            "maker": 0.0008,
            "taker_margin": 0.001,
            "maker_margin": 0.0008,
            "taker_futures": 0.0005,
            "maker_futures": 0.0002,
        },
        "features": {"spot": True, "margin_isolated": True, "margin_cross": True, "futures": True},
        "max_leverage": {"spot": 1, "margin_isolated": 10, "margin_cross": 10, "futures": 100},
        "public": {"url": "https://www.okx.com", "ping": "/api/v5/public/time"},
        "testnet": {
            "spot": {"url": "https://www.okx.com", "ping": "/api/v5/public/time", "header": "x-simulated-trading: 1"},
            "note": "Демо-торговля OKX: заголовок x-simulated-trading: 1 (ключи с демо-проекта).",
        },
    },
    "pionex": {
        "name": "Pionex",
        "fees": {"taker": 0.0005, "maker": 0.0005},
        "features": {"spot": True, "margin_isolated": False, "margin_cross": False, "futures": False},
        "max_leverage": {"spot": 1, "margin_isolated": 1, "margin_cross": 1, "futures": 1},
        "public": {"url": "https://api.pionex.com", "ping": "/api/v1/market/tickers?symbol=BTC_USDT"},
        "testnet": None,
    },
}

# Human-readable market modes (order matters for the UI selects).
MARKET_MODES: tuple[str, ...] = ("spot", "margin_isolated", "margin_cross", "futures")

MARKET_MODE_LABELS: dict[str, str] = {
    "spot": "Спот",
    "margin_isolated": "Маржа (изолир.)",
    "margin_cross": "Маржа (кросс)",
    "futures": "Фьючерсы",
}

MODE_FEE_KEY: dict[str, str] = {
    "spot": "taker",
    "margin_isolated": "taker_margin",
    "margin_cross": "taker_margin",
    "futures": "taker_futures",
}


def catalog_entry(exchange: str) -> dict[str, Any] | None:
    return EXCHANGE_CATALOG.get((exchange or "").strip().lower())


def exchange_catalog(exchange: str = "") -> dict[str, Any]:
    """Return the catalog for one exchange, or all sorted alphabetically."""
    if exchange:
        return {exchange: EXCHANGE_CATALOG[exchange]} if exchange in EXCHANGE_CATALOG else {}
    return {name: EXCHANGE_CATALOG[name] for name in sorted(EXCHANGE_CATALOG)}


def supports_mode(exchange: str, mode: str) -> bool:
    entry = catalog_entry(exchange)
    if not entry:
        return mode == "spot"
    features = entry.get("features") or {}
    return bool(features.get(mode, False))


def default_fee(exchange: str, mode: str = "spot") -> float:
    """Fallback fee for an exchange+mode when no per-market fee is available."""
    entry = catalog_entry(exchange)
    if not entry:
        return 0.001
    fees = entry.get("fees") or {}
    key = MODE_FEE_KEY.get(mode, "taker")
    rate = fees.get(key) or fees.get("taker") or fees.get("maker") or 0.001
    return float(rate)


def effective_leverage(exchange: str, mode: str, requested: float) -> float:
    """Cap requested leverage by exchange/mode limits; spot is always 1x."""
    if mode == "spot":
        return 1.0
    entry = catalog_entry(exchange)
    caps = (entry or {}).get("max_leverage") or {}
    cap = caps.get(mode) or (10 if mode != "futures" else 100)
    try:
        requested = float(requested)
    except (TypeError, ValueError):
        requested = 1.0
    if not requested > 0:
        requested = 1.0
    return float(min(requested, cap))


def mode_label(mode: str) -> str:
    return MARKET_MODE_LABELS.get(mode, mode)