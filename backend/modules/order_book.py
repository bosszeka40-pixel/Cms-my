"""Реальный стакан (L2 order book) с подключённых бирж + метрики ликвидности.

Снапшоты берутся из публичного API биржи (CCXT fetch_order_book) и коротко
кэшируются, чтобы бот и UI не долбили эндпоинт. depth_features() превращает
сырой стакан в числовые фичи, которыми бот дополняет свои торговые сигналы.
"""
from __future__ import annotations

import time
from threading import Lock

DEFAULT_LIMIT = 20
DEPTH_TTL = 3.0

_SNAPSHOTS: dict = {}
_LOCK = Lock()


def fetch_order_book_snapshot(
    client,
    pair: str,
    limit: int = DEFAULT_LIMIT,
    ttl: float = DEPTH_TTL,
) -> dict:
    """Достаёт свежий стакан, при неудаче возвращает последний кэш."""
    key = (id(client), pair, limit)
    now = time.time()
    with _LOCK:
        hit = _SNAPSHOTS.get(key)
        if hit and now - hit[1] < ttl:
            return hit[0]
    raw = client.fetch_order_book(pair, limit=limit)
    snapshot = _normalize(raw, limit)
    with _LOCK:
        _SNAPSHOTS[key] = (snapshot, time.time())
    return snapshot


def _normalize(raw: dict, limit: int) -> dict:
    bids = raw.get("bids") or []
    asks = raw.get("asks") or []
    top_bids = [[float(price), float(volume)] for price, volume in bids[:limit]]
    top_asks = [[float(price), float(volume)] for price, volume in asks[:limit]]
    best_bid = top_bids[0][0] if top_bids else None
    best_ask = top_asks[0][0] if top_asks else None
    mid = None
    if best_bid is not None and best_ask is not None:
        mid = (best_bid + best_ask) / 2.0
    elif best_bid is not None:
        mid = best_bid
    elif best_ask is not None:
        mid = best_ask
    spread = None
    if best_bid is not None and best_ask is not None and best_ask >= best_bid:
        spread = best_ask - best_bid
    return {
        "ts": int(raw.get("timestamp") or time.time() * 1000),
        "bids": top_bids,
        "asks": top_asks,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": mid,
        "spread": spread,
    }


def depth_features(order_book: dict) -> dict:
    """Числовые фичи стакана для стратегий и обучения бота."""
    bids = order_book.get("bids") or []
    asks = order_book.get("asks") or []
    bid_vol = sum(volume for _price, volume in bids) or 0.0
    ask_vol = sum(volume for _price, volume in asks) or 0.0
    mid = order_book.get("mid")
    spread = order_book.get("spread")
    spread_pct = (spread / mid) if mid and spread is not None else 0.0
    total = bid_vol + ask_vol
    imbalance = (bid_vol - ask_vol) / total if total > 0 else 0.0
    bid_side_pct = (bid_vol / total * 100.0) if total > 0 else 50.0
    top3_bid = sum(volume for _price, volume in bids[:3])
    top3_ask = sum(volume for _price, volume in asks[:3])
    liquidity = min(top3_bid, top3_ask)
    return {
        "spread_pct": round(min(spread_pct, 1.0), 8),
        "imbalance": round(imbalance, 6),
        "bid_side_pct": round(bid_side_pct, 4),
        "depth_bid": round(bid_vol, 8),
        "depth_ask": round(ask_vol, 8),
        "bid_depth_ratio": round(bid_vol / ask_vol, 6) if ask_vol > 0 else 1.0,
        "liquidity_score": round(liquidity, 8),
        "mid": float(mid) if mid is not None else None,
    }


def merge_features(order_book: dict) -> dict:
    """Стакан + метирики в одном JSON для UI и бота."""
    metrics = depth_features(order_book)
    return {**order_book, "metrics": metrics}