"""Простой TTL-кеш в памяти для публичных market данных.

Защищает от зависаний и 500 наружу, возвращая кэшированные данные,
если внешний запрос (CCXT/новости) не отвечает вовремя.
"""
import time
from threading import Lock

_cache: dict = {}
_lock = Lock()


def cached_fetch(key, ttl, producer):
    now = time.time()
    with _lock:
        entry = _cache.get(key)
        if entry and (now - entry[1]) < ttl:
            return entry[0], True
    try:
        result = producer()
    except Exception:
        if entry:
            return entry[0], True
        raise
    with _lock:
        _cache[key] = (result, time.time())
    return result, False


def cached_get(key):
    with _lock:
        entry = _cache.get(key)
        return entry[0] if entry else None
