"""Просчёт торгового терминала: живая ставка биржи, конвертация «валюта <-> монеты»,
комиссия и маржа во всех режимах (spot/margin/futures).

Данные всегда берутся напрямую с биржи, на которой идёт торговля, через публичный API
(fetch_ticker / load_markets) той же биржи. Модуль только рассчитывает: валюту котировки,
количество монет, эквивалент в EUR и USDT, комиссию, маржу с плечом и лимиты точности/мин-лота.
Таким образом можно задать сумму в USDT (или EUR, или в самих монетах) и сразу видеть
парный объём — для всех пар, поддерживаемых биржей из списка, разрешённого боту.

Семантика EUR: EUR — это валюта расчёта «реальной стоимости» монет на нашем стеке.
Ведите сумму покупки в EUR — стоимость монет будет посчитана по живому курсу той же
биржи (EUR/USDT -> USDT -> котировка). Если же пара реально торгуется с EUR
(например EUR/USDT), то EUR — это валюта котировки пары и участвует как обычная монета.
"""
from __future__ import annotations

import math
import threading
import time

CACHE_TICKER_TTL = 3.0
CACHE_MARKETS_TTL = 300.0

_ticker_cache: dict[tuple[str, str], tuple[float, dict]] = {}
_markets_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()

SUPPORTED_UNITS = ("quote", "base", "eur")


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cache_get(cache: dict, key, ttl: float):
    with _lock:
        row = cache.get(key)
        if row is not None and time.time() - row[0] < ttl:
            return row[1]
    return None


def _cache_put(cache: dict, key, value):
    with _lock:
        cache[key] = (time.time(), value)


def live_ticker(client, exchange: str, pair: str) -> dict:
    """Живая котировка с биржи (публичный API). Кэш 3 сек на (exchange, pair)."""
    key = (exchange or "binance").lower(), pair.upper()
    cached = _cache_get(_ticker_cache, key, CACHE_TICKER_TTL)
    if cached is not None:
        return cached
    ticker = client.fetch_ticker(pair)
    last = _num(ticker.get("last")) or _num(ticker.get("close"))
    bid = _num(ticker.get("bid")) or last
    ask = _num(ticker.get("ask")) or last
    mid = (bid + ask) / 2.0 if bid is not None and ask is not None else None
    result = {
        "last": last,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "change_pct": ticker.get("percentage"),
        "quote_volume": _num(ticker.get("quoteVolume")),
        "ts": int(time.time() * 1000),
    }
    if result["last"] is None and result["bid"] is None and result["ask"] is None:
        raise ValueError(f"Биржа не вернула цену для {pair}.")
    _cache_put(_ticker_cache, key, result)
    return result


def market_meta(client, exchange: str, pair: str) -> dict:
    """Параметры инструмента с биржи: точность, мин. лот, мин. номинал. Кэш 5 мин."""
    key = (exchange or "binance").lower()
    markets = _cache_get(_markets_cache, key, CACHE_MARKETS_TTL)
    if markets is None:
        markets = client.load_markets()
        _cache_put(_markets_cache, key, markets)
    market = markets.get(pair) or {}
    limits = market.get("limits") or {}
    precision = market.get("precision") or {}
    return {
        "pair": pair,
        "base": market.get("base") or pair.split("/")[0],
        "quote": market.get("quote") or pair.split("/")[-1],
        "active": market.get("active", True),
        "precision_amount": _num(precision.get("amount")),
        "precision_price": _num(precision.get("price")),
        "min_amount": _num(limits.get("amount", {}).get("min")),
        "max_amount": _num(limits.get("amount", {}).get("max")),
        "min_notional": (
            _num(limits.get("cost", {}).get("min"))
            or _num(limits.get("price", {}).get("min"))
        ),
    }


def eur_per_quote(client, exchange: str, quote: str) -> float | None:
    """Сколько EUR в 1 единице валюты котировки (живой курс с той же биржи).

    Pipelines: EUR -> USDT -> произвольная котировка (USDC и т.п.). Если биржа
    не даёт курс EUR/USDT, возвращается None (EUR-счет не активен) — курс не выдумываем.
    """
    quote = (quote or "USDT").upper()
    if quote == "EUR":
        return 1.0
    try:
        eurusdt = _num(live_ticker(client, exchange, "EUR/USDT")["last"])
    except Exception:
        eurusdt = None
    if not eurusdt:
        return None
    eur_per_usdt = 1.0 / eurusdt
    if quote == "USDT":
        return eur_per_usdt
    if quote == "USDC":
        try:
            usdc_usdt = _num(live_ticker(client, exchange, "USDC/USDT")["last"])
        except Exception:
            usdc_usdt = None
        if not usdc_usdt:
            return None
        return eur_per_usdt * usdc_usdt
    return None


def pair_units(client, exchange: str, pair: str) -> list[str]:
    """Реальные доступные единицы ввода для пары: валюта котировки, монета, EUR."""
    base = pair.split("/")[0]
    quote = pair.split("/")[-1]
    units = ["quote", "base"]
    if eur_per_quote(client, exchange, quote) is not None:
        units.append("eur")
    return units


def preview(client, exchange: str, pair: str, market_mode: str, side: str,
            unit: str, value, fee_rate: float, leverage: float) -> dict:
    """Полный просчёт ордера по реальной цене биржи.

    unit = "quote"  — value это сумма в валюте котировки (например USDT)
    unit = "base"   — value это количество монет (например DOT)
    unit = "eur"    — value это сумма в евро
    side = "buy"|"sell" — определяет, по какой цене считается исполнение (ask/bid).
    """
    unit = (unit or "quote").lower()
    if unit not in SUPPORTED_UNITS:
        raise ValueError("unit должен быть одним из: quote, base, eur")
    side = (side or "buy").lower()
    if side not in {"buy", "sell"}:
        raise ValueError("side должен быть buy или sell")
    if pair.count("/") != 1 or not pair.split("/")[0] or not pair.split("/")[1]:
        raise ValueError("Неверный формат пары, ожидается БАЗА/КОТИРОВКА (например DOT/USDT).")
    base, quote = pair.split("/")
    value = _num(value) or 0.0

    tk = live_ticker(client, exchange, pair)
    bid, ask, last = tk["bid"], tk["ask"], tk["last"]
    exec_price = ask if side == "buy" else bid
    if not exec_price:
        exec_price = last

    eur_rate = eur_per_quote(client, exchange, quote)

    if unit == "quote":
        quote_value = value
    elif unit == "base":
        quote_value = value * (exec_price or 0.0)
    else:  # eur
        if not eur_rate:
            raise ValueError("EUR-счёт не доступен: биржа не отдаёт курс EUR/USDT.")
        quote_value = value / eur_rate if eur_rate else 0.0

    qty = quote_value / exec_price if (exec_price and quote_value is not None) else 0.0
    eur_value = quote_value * eur_rate if (quote_value is not None and eur_rate) else None

    notional = quote_value * leverage if quote_value is not None else None
    fee_quote = notional * fee_rate if notional is not None else None
    fee_eur = fee_quote * eur_rate if (fee_quote is not None and eur_rate) else None
    margin_quote = quote_value / leverage if (quote_value is not None and leverage) else quote_value

    meta = market_meta(client, exchange, pair)
    qty_rounded = _round_amount(client, pair, qty, meta.get("precision_amount"))

    warnings = []
    if meta.get("min_notional") and quote_value is not None and 0 < quote_value < meta["min_notional"]:
        warnings.append(f"Номинал меньше минимального {meta['min_notional']} {quote}")
    if meta.get("min_amount") and qty_rounded and 0 < qty_rounded < meta["min_amount"]:
        warnings.append(f"Количество меньше минимального {meta['min_amount']} {base}")

    eur_symbol = "EUR"
    return {
        "pair": f"{base}/{quote}",
        "base": base,
        "quote": quote,
        "exchange": (exchange or "binance").lower(),
        "market_mode": market_mode,
        "side": side,
        "unit": unit,
        "value": round(value, 10),
        "units": ["quote", "base"] + (["eur"] if eur_rate else []),
        "rate": {
            "bid": round(bid, 8) if bid is not None else None,
            "ask": round(ask, 8) if ask is not None else None,
            "last": round(last, 8) if last is not None else None,
            "mid": round((bid + ask) / 2.0, 8) if bid is not None and ask is not None else None,
        },
        "exec_price": round(exec_price, 8) if exec_price else None,
        "quote_value": round(quote_value, 10) if quote_value is not None else None,
        "qty": round(qty, 12) if qty else 0.0,
        "qty_rounded": qty_rounded,
        "eur_rate": round(eur_rate, 10) if eur_rate else None,
        "eur_value": round(eur_value, 4) if eur_value is not None else None,
        "notional_quote": round(notional, 8) if notional is not None else None,
        "fee_rate": fee_rate,
        "leverage": leverage,
        "fee_quote": round(fee_quote, 10) if fee_quote is not None else None,
        "fee_eur": round(fee_eur, 4) if fee_eur is not None else None,
        "margin_quote": round(margin_quote, 8) if margin_quote is not None else None,
        "margin_eur": round(margin_quote * eur_rate, 4) if (margin_quote is not None and eur_rate) else None,
        "min_amount": meta.get("min_amount"),
        "min_notional": meta.get("min_notional"),
        "precision_amount": meta.get("precision_amount"),
        "warnings": warnings,
        "ts": tk["ts"],
    }


def _round_amount(client, pair: str, qty: float, precision_amount) -> float:
    amount_to_precision = getattr(client, "amount_to_precision", None)
    try:
        if amount_to_precision is not None and qty is not None and qty > 0:
            return float(amount_to_precision(pair, qty))
    except Exception:
        pass
    decimals = 8
    if precision_amount and precision_amount > 0:
        try:
            decimals = int(round(-math.log10(precision_amount))) if precision_amount < 1 else 0
        except (ValueError, OverflowError):
            decimals = 8
    return float(round(qty, max(0, min(8, decimals))))


def pair_listing(client, exchange: str, allowed_pairs: tuple[str, ...]) -> list[dict]:
    """Доступные боту пары на бирже с параметрами инструмента (реальный API биржи).

    Включает нативный символ биржи (``id``), чтобы терминал в браузере мог обращаться
    к публичному API биржи напрямую (без нагрузки нашего сервера): binance символ
    "DOTUSDT", okx "DOT-USDT", bitfinex "tDOTUST" и т.д.
    """
    markets = client.load_markets()
    result = []
    for pair in allowed_pairs:
        market = markets.get(pair)
        if not market:
            continue
        meta = {
            "pair": pair,
            "id": market.get("id") or market.get("symbol") or pair.replace("/", ""),
            "base": market.get("base") or pair.split("/")[0],
            "quote": market.get("quote") or pair.split("/")[-1],
            "active": market.get("active", True),
            "swap": bool(market.get("swap")),
            "settle": market.get("settle"),
        }
        limits = market.get("limits") or {}
        precision = market.get("precision") or {}
        meta["min_amount"] = _num(limits.get("amount", {}).get("min"))
        meta["min_notional"] = _num(limits.get("cost", {}).get("min")) or _num(limits.get("price", {}).get("min"))
        meta["precision_amount"] = _num(precision.get("amount"))
        meta["precision_price"] = _num(precision.get("price"))
        result.append(meta)
    return result