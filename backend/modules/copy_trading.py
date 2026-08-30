"""Копитрейдинг: подписка на стратегии-лидеров и зеркалирование их сделок в свой счёт.

Лидер = стратегия (ready-made "трейдер"). Подписчик задаёт долю/сумму в EUR, биржу,
режим и плечо; цикл зеркалирования (pulse) считает реальное направление лидера из
рыночного контекста той же биржи (свечи + стакан + ИИ-слой), и при смене сигнала или
истечении периода исполняет копию на демо-балансе подписчика по его настройкам.

Состояние персистится в JSON (atomic tmp+replace), переживает рестарт сервера.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time

DEFAULT_SETTINGS = {
    "amount_eur": 10.0,
    "mode": "demo",
    "strategy": "auto",
    "exchange": "binance",
    "market_mode": "spot",
    "leverage": 1.5,
    "pair": "BTC/USDT",
    "active": True,
}


class CopyTradingStore:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._data = {"follows": {}, "mirrors": {}}
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._data = {
                    "follows": data.get("follows") or {},
                    "mirrors": data.get("mirrors") or {},
                }
        except (OSError, ValueError):
            self._data = {"follows": {}, "mirrors": {}}

    def _save(self):
        directory = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ----- подписки -----
    def follows(self, email: str) -> dict:
        return dict(self._data["follows"].get(email, {}))

    def follow(self, email: str, leader: str, settings: dict) -> dict:
        with self._lock:
            entry = dict(DEFAULT_SETTINGS)
            entry.update({k: v for k, v in (settings or {}).items() if v is not None})
            entry["created_ts"] = int(time.time())
            entry["active"] = True
            self._data["follows"].setdefault(email, {})[leader] = entry
            self._save()
            return entry

    def unfollow(self, email: str, leader: str) -> bool:
        with self._lock:
            had = self._data["follows"].get(email, {}).pop(leader, None)
            if had is not None:
                self._save()
            return had is not None

    def reset(self, email: str):
        with self._lock:
            self._data["follows"].pop(email, None)
            self._data["mirrors"].pop(email, None)
            self._save()

    # ----- зеркалирование -----
    def mirror_state(self, email: str, leader: str) -> dict:
        return dict(self._data["mirrors"].get(email, {}).get(leader, {}))

    def record_mirror(self, email: str, leader: str, record: dict, keep: int = 40):
        with self._lock:
            mirrors = self._data["mirrors"].setdefault(email, {}).setdefault(leader, {})
            history = mirrors.get("history") or []
            history.append({
                "ts": int(time.time()),
                "side": record.get("side"),
                "direction": record.get("direction"),
                "pnl": record.get("pnl"),
                "amount_eur": record.get("amount_eur"),
                "pair": record.get("pair"),
                "exchange": record.get("exchange"),
                "market_mode": record.get("market_mode"),
                "leverage": record.get("leverage"),
                "signal": record.get("signal"),
            })
            mirrors["history"] = history[-keep:]
            mirrors["last_side"] = record.get("side")
            mirrors["last_ts"] = int(time.time())
            mirrors["last_pnl"] = record.get("pnl")
            mirrors["total_pnl"] = round(float(mirrors.get("total_pnl") or 0.0) + float(record.get("pnl") or 0.0), 4)
            self._save()

    def portfolio(self, email: str) -> dict:
        follows = self.follows(email)
        items = []
        for leader, settings in follows.items():
            m = self.mirror_state(email, leader)
            items.append({
                "leader": leader,
                "settings": settings,
                "last_side": m.get("last_side"),
                "last_ts": m.get("last_ts"),
                "last_pnl": m.get("last_pnl"),
                "total_pnl": m.get("total_pnl"),
                "mirror_count": len(m.get("history") or []),
            })
        return {"follows": items, "count": len(follows)}

    def stats(self) -> dict:
        emails = set(self._data["follows"]) | set(self._data["mirrors"])
        total_follows = sum(len(self._data["follows"].get(e, {})) for e in emails)
        return {
            "users": len(emails),
            "follows": total_follows,
            "mirrors": sum(
                sum(len((m or {}).get("history") or []) for m in self._data["mirrors"].get(e, {}).values())
                for e in self._data["mirrors"]
            ),
        }