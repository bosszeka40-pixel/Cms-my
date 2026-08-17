import math
import os
from datetime import datetime

import numpy as np


MAX_SERIES_LENGTH = 5000
MAX_LEVERAGE = 2.0


class AICryptoMemoryBrain:
    def __init__(self):
        self.memory_history = []
        self.params = {
            "leverage": 2.0,
            "fee": float(os.getenv("HFT_FEE_RATE", "0.0001")),
            "ai_confidence_cutoff": 0.38,
        }
        if not math.isfinite(self.params["fee"]) or not 0 <= self.params["fee"] <= 0.05:
            self.params["fee"] = 0.0001

    def record_action(self, action_type: str, result_roi: float):
        if not math.isfinite(float(result_roi)):
            return
        self.memory_history.append(
            {
                "action": action_type,
                "roi": float(result_roi),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def summarize(self):
        return {
            "actions": len(self.memory_history),
            "history": self.memory_history,
        }


class CMSProductionHFTBot:
    def __init__(self, initial_capital: float = 100.0, brain: AICryptoMemoryBrain | None = None):
        if not math.isfinite(float(initial_capital)) or initial_capital <= 0:
            raise ValueError("Начальный капитал должен быть положительным конечным числом.")
        self.capital = float(initial_capital)
        self.brain = brain or AICryptoMemoryBrain()
        self.trade_history = []

    def trade_loop(self, market_data, ai_stream):
        if len(market_data) != len(ai_stream):
            raise ValueError("market_data and ai_stream must be the same length")
        if len(market_data) > MAX_SERIES_LENGTH:
            raise ValueError(f"Слишком большой набор данных: максимум {MAX_SERIES_LENGTH} точек.")
        if len(market_data) < 3:
            raise ValueError("Нужно минимум 3 точки рыночных данных.")

        prices = np.asarray(market_data, dtype=float)
        confidences = np.asarray(ai_stream, dtype=float)
        if not np.all(np.isfinite(prices)) or not np.all(np.isfinite(confidences)):
            raise ValueError("Рыночные данные и AI confidence должны быть конечными числами.")
        if np.any(prices <= 0):
            raise ValueError("Цены должны быть положительными.")
        if not np.isfinite(self.brain.params["leverage"]) or not 0 < self.brain.params["leverage"] <= MAX_LEVERAGE:
            raise ValueError("Плечо HFT должно быть в диапазоне 0..2x.")

        # The signal at index i may use only candles through i. The next
        # candle is used solely to settle the already-created trade.
        for i in range(1, len(prices) - 1):
            observed_change = prices[i] - prices[i - 1]
            next_change = prices[i + 1] - prices[i]
            pct_change = next_change / prices[i]
            confidence = confidences[i]

            if abs(observed_change) > 35.0 and confidence > self.brain.params["ai_confidence_cutoff"]:
                direction = 1 if observed_change > 0 else -1
                net_ret = (direction * pct_change * self.brain.params["leverage"]) - self.brain.params["fee"]
                if not math.isfinite(float(net_ret)):
                    raise ValueError("HFT рассчитал некорректную доходность.")
                self.capital *= 1 + net_ret
                if not math.isfinite(self.capital) or self.capital <= 0:
                    raise ValueError("HFT привёл к некорректному капиталу; операция остановлена.")
                action = "long" if direction > 0 else "short"
                self.brain.record_action(action, net_ret)
                self.trade_history.append(
                    {
                        "index": i,
                        "action": action,
                        "price": float(prices[i]),
                        "next_price": float(prices[i + 1]),
                        "signal_change": float(observed_change),
                        "roi": float(net_ret),
                        "capital": float(self.capital),
                    }
                )

        return float(self.capital)

    def metrics(self):
        return {
            "capital": float(self.capital),
            "trades": len(self.trade_history),
            "trade_history": self.trade_history,
            "brain_summary": self.brain.summarize(),
        }
