"""Онлайн-обучение бота на реальных сделках (SGD logistic).

Бот учится на наблюдениях: вектор фич (свечи + стакан) -> чем закончилась сделка
(+/-). Веса сохраняются в JSON между перезапусками. Без ИИ можно вообще не
использовать: стратегия работает на эвристическом сентименте.
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from pathlib import Path
from threading import Lock

from .market_features import FEATURE_NAMES


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class OnlineSignalLearner:
    """Логистическая SGD-модель «вероятность роста после сигнала»."""

    def __init__(
        self,
        state_path: str | Path | None = None,
        learning_rate: float = 0.05,
        enabled: bool = True,
        confidence_cutoff: float = 0.62,
    ):
        self.n_features = len(FEATURE_NAMES)
        self.learning_rate = float(os.getenv("LEARNER_LEARNING_RATE", learning_rate))
        self.enabled = bool(os.getenv("LEARNER_ENABLED", "1") == "1") and enabled
        self.confidence_cutoff = float(
            os.getenv("LEARNER_CONFIDENCE_CUTOFF", confidence_cutoff)
        )
        self.state_path = Path(state_path) if state_path else None
        self._lock = Lock()
        self.weights = [random.uniform(-0.05, 0.05) for _ in range(self.n_features)]
        self.bias = 0.0
        self.train_count = 0
        self.wins = 0
        self.losses = 0
        self.last_features = []
        self.last_label = None
        self.last_confidence = None
        self._loaded = False
        self._load()

    # ── persistence ────────────────────────────────────────────────────
    def _load(self):
        if not self.state_path or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if len(data.get("weights", [])) == self.n_features:
                self.weights = [float(w) for w in data["weights"]]
                self.bias = float(data.get("bias", 0.0))
                self.train_count = int(data.get("train_count", 0))
                self.wins = int(data.get("wins", 0))
                self.losses = int(data.get("losses", 0))
            self._loaded = True
        except (ValueError, OSError, TypeError):
            pass

    def _save(self):
        if not self.state_path:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "feature_names": FEATURE_NAMES,
                "weights": self.weights,
                "bias": self.bias,
                "train_count": self.train_count,
                "wins": self.wins,
                "losses": self.losses,
                "updated_at": int(time.time()),
            }
            tmp = self.state_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(self.state_path)
        except OSError:
            pass

    # ── model ──────────────────────────────────────────────────────────
    def predict_confidence(self, features: list[float]) -> float:
        """Вероятность направления вверх в [0, 1]. 0.5 — нет уверенности."""
        vec = _normalize(features, self.n_features)
        if vec is None:
            self.last_confidence = 0.5
            return 0.5
        linear = self.bias + sum(w * x for w, x in zip(self.weights, vec))
        conf = _sigmoid(linear)
        self.last_features = list(vec)
        self.last_confidence = float(conf)
        return float(conf)

    def suggest_direction(self, confidence: float | None = None) -> int:
        """-1/0/1 — направление от ИИ при достаточной уверенности."""
        conf = confidence if confidence is not None else self.last_confidence
        if conf is None:
            return 0
        if conf >= self.confidence_cutoff:
            return 1
        if conf <= 1.0 - self.confidence_cutoff:
            return -1
        return 0

    def update(self, features: list[float], realized_roi: float):
        """Один шаг SGD по факту исхода сделки (не учимся на неопределённости)."""
        if not math.isfinite(float(realized_roi)):
            return
        vec = _normalize(features, self.n_features)
        if vec is None:
            return
        label = 1.0 if realized_roi > 0 else -1.0
        with self._lock:
            self.train_count += 1
            if label > 0:
                self.wins += 1
            else:
                self.losses += 1
            linear = self.bias + sum(w * x for w, x in zip(self.weights, vec))
            pred = _sigmoid(linear)
            error = label - pred
            grad_scale = self.learning_rate * error
            self.weights = [
                w + grad_scale * x * pred * (1.0 - pred)
                for w, x in zip(self.weights, vec)
            ]
            self.bias += grad_scale * pred * (1.0 - pred)
            self.last_label = label
            self._save()

    def reset(self, seed_train: int = 0):
        with self._lock:
            self.weights = [random.uniform(-0.05, 0.05) for _ in range(self.n_features)]
            self.bias = 0.0
            self.train_count = seed_train
            self.wins = 0
            self.losses = 0
            self.last_features = []
            self.last_label = None
            self.last_confidence = None
            self._save()

    # ── stats ──────────────────────────────────────────────────────────
    def stats(self) -> dict:
        with self._lock:
            wins = self.wins
            losses = self.losses
        total = wins + losses
        win_rate = (wins / total) if total else None
        return {
            "enabled": self.enabled,
            "feature_names": list(FEATURE_NAMES),
            "weights": dict(zip(FEATURE_NAMES, [round(w, 6) for w in self.weights])),
            "bias": round(self.bias, 6),
            "train_count": self.train_count,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4) if win_rate is not None else None,
            "last_confidence": self.last_confidence,
            "last_features": self.last_features[-8:] if self.last_features else [],
            "last_label": self.last_label,
            "cutoff": self.confidence_cutoff,
            "learning_rate": self.learning_rate,
            "persisted": bool(self.state_path),
            "loaded": self._loaded,
        }


def _normalize(features, n):
    vec = list(features)[:n]
    if len(vec) != n:
        return None
    for value in vec:
        if not math.isfinite(float(value)):
            return None
    return tuple(max(-2.0, min(2.0, float(x))) for x in vec)