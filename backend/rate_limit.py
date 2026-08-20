from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def __call__(self, request: Request) -> None:
        now = monotonic()
        key = f'{request.client.host if request.client else "unknown"}:{request.url.path}'
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                raise HTTPException(status_code=429, detail='Слишком много запросов. Повторите позже.')
            events.append(now)

cmsc_quote_rate_limit = InMemoryRateLimiter(limit=20, window_seconds=60)
cmsc_intent_rate_limit = InMemoryRateLimiter(limit=5, window_seconds=60)
