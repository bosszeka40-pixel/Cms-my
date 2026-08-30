"""Реальные рыночные фичи из свечей (график) для стратегий и обучения.

Считает: momentum за 1h/4h/1d, RSI(14), объёмный коэффициент, разрыв EMA7/EMA25,
ATR%. Вход — ccxt-style свечи: [ts, open, high, low, close, volume].
"""
from __future__ import annotations

import math


def closes_of(candles) -> list[float]:
    return [
        float(_row(c, 4))
        for c in candles
        if c and _row(c, 4) is not None and math.isfinite(float(_row(c, 4)))
    ]


def _row(candle, index):
    """Свеча может быть ccxt-списком или словарём из БД."""
    if isinstance(candle, dict):
        key = ("timestamp", "open", "high", "low", "close", "volume")[index]
        return candle.get(key)
    if isinstance(candle, (list, tuple)) and len(candle) > index:
        return candle[index]
    return None


def last_close(candles) -> float | None:
    values = closes_of(candles)
    return values[-1] if values else None


def rsi(closes: list[float], period: int = 14) -> float:
    """RSI(period) по закрытиям. Нет данных — нейтральные 50."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def ema(closes: list[float], period: int) -> float:
    if not closes:
        return 0.0
    k = 2.0 / (period + 1)
    value = closes[0]
    for c in closes[1:]:
        value = c * k + value * (1 - k)
    return value


def candle_features(candles_1h: list, candles_1d: list | None = None) -> dict:
    """Фичи на основе реальных свечей. Пустой результат — данных нет."""
    h1 = closes_of(candles_1h) if candles_1h else []
    if not h1:
        return {}
    last = h1[-1]
    prev = h1[-2] if len(h1) > 1 else last

    def pct(now, then):
        if not then:
            return 0.0
        return (now - then) / then * 100.0

    daily = closes_of(candles_1d) if candles_1d else None
    daily = daily or h1
    day_ref = daily[-1] if daily else last

    vols = [
        float(_row(c, 5) or 0.0)
        for c in candles_1h
        if _row(c, 5) is not None and math.isfinite(float(_row(c, 5)))
    ]
    vol_last = vols[-1] if vols else 0.0
    vol_avg = (sum(vols[:-1]) / len(vols[:-1])) if len(vols) > 1 else vol_last
    vol_ratio = (vol_last / vol_avg) if vol_avg > 0 else 1.0

    e7 = ema(h1, 7)
    e25 = ema(h1, 25)
    ema_gap = pct(e7, e25) if e25 else 0.0

    recent_high = max(float(_row(c, 2)) for c in candles_1h if _row(c, 2) is not None)
    recent_low = min(float(_row(c, 3)) for c in candles_1h if _row(c, 3) is not None)
    atr = ((recent_high - recent_low) / last * 100.0) if last else 0.0

    return {
        "last_price": float(last),
        "momentum_1h": round(pct(last, prev), 6),
        "momentum_4h": round(pct(last, h1[-5]) if len(h1) > 4 else pct(last, prev), 6),
        "momentum_1d": round(pct(last, day_ref), 6),
        "rsi14": round(rsi(h1, 14), 4),
        "vol_ratio": round(min(vol_ratio, 10.0), 4),
        "ema_gap": round(min(ema_gap, 10.0), 6),
        "atr_pct": round(min(atr, 50.0), 6),
    }


def feature_vector(candle_feat: dict, depth_feat: dict | None = None) -> list[float] | None:
    """Нормализованный вектор фич для обучения бота. None — данных мало."""
    if not candle_feat:
        return None
    depth_feat = depth_feat or {}
    rsi_norm = (candle_feat.get("rsi14", 50.0) - 50.0) / 50.0
    return [
        max(-1.0, min(1.0, candle_feat.get("momentum_1h", 0.0) / 2.0)),
        max(-1.0, min(1.0, candle_feat.get("momentum_4h", 0.0) / 4.0)),
        max(-1.0, min(1.0, candle_feat.get("momentum_1d", 0.0) / 8.0)),
        rsi_norm,
        max(-1.0, min(1.0, (candle_feat.get("vol_ratio", 1.0) - 1.0) / 3.0)),
        max(-1.0, min(1.0, candle_feat.get("ema_gap", 0.0) / 2.0)),
        max(-1.0, min(1.0, depth_feat.get("imbalance", 0.0) * 3.0)),
        max(-1.0, min(1.0, depth_feat.get("spread_pct", 0.0) * 100.0)),
    ]


FEATURE_NAMES = [
    "momentum_1h",
    "momentum_4h",
    "momentum_1d",
    "rsi14",
    "vol_ratio",
    "ema_gap",
    "imbalance",
    "spread_pct",
]


def heuristic_sentiment(candle_feat: dict, depth_feat: dict | None = None) -> float:
    """Сентимент без ИИ: реальные свечи + стакан (дисбаланс спроса)."""
    if not candle_feat:
        return 0.0
    depth_feat = depth_feat or {}
    momentum = max(-1.0, min(1.0, candle_feat.get("momentum_1h", 0.0) / 1.5))
    imbalance = max(-1.0, min(1.0, depth_feat.get("imbalance", 0.0) * 3.0))
    rsi_v = candle_feat.get("rsi14", 50.0)
    if rsi_v >= 70:
        rsi_edge = -0.3
    elif rsi_v <= 30:
        rsi_edge = 0.3
    else:
        rsi_edge = (rsi_v - 50.0) / 150.0
    value = 0.45 * momentum + 0.35 * imbalance + 0.2 * rsi_edge
    return max(-1.0, min(1.0, value))