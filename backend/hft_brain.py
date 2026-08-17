import numpy as np
import os
from datetime import datetime


class AICryptoMemoryBrain:
    def __init__(self):
        self.memory_history = []
        self.params = {
            "leverage": 3.0,
            "fee": float(os.getenv("HFT_FEE_RATE", "0.0001")),
            "ai_confidence_cutoff": 0.38,
        }

    def record_action(self, action_type: str, result_roi: float):
        self.memory_history.append({
            "action": action_type,
            "roi": result_roi,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def summarize(self):
        return {
            "actions": len(self.memory_history),
            "history": self.memory_history,
        }


class CMSProductionHFTBot:
    """Simulation-only HFT model.

    This class calculates simulated trades from supplied market data. It has
    deliberately no exchange client and no order/cancel capability. Real
    execution belongs exclusively behind the central execution gateway.
    """

    simulation_only = True

    def __init__(self, initial_capital: float = 100.0, brain: AICryptoMemoryBrain | None = None):
        self.capital = initial_capital
        self.brain = brain or AICryptoMemoryBrain()
        self.trade_history = []

    def trade_loop(self, market_data, ai_stream):
        if not self.simulation_only:
            raise RuntimeError("CMSProductionHFTBot is simulation-only")
        if len(market_data) != len(ai_stream):
            raise ValueError("market_data and ai_stream must be the same length")

        prices = np.array(market_data, dtype=float)
        confidences = np.array(ai_stream, dtype=float)

        # The signal at index i may use only candles through i. The next
        # candle is used solely to settle the already-created simulated trade.
        for i in range(1, len(prices) - 1):
            observed_change = prices[i] - prices[i - 1]
            next_change = prices[i + 1] - prices[i]
            pct_change = next_change / prices[i] if prices[i] != 0 else 0.0
            confidence = confidences[i]

            if abs(observed_change) > 35.0 and confidence > self.brain.params["ai_confidence_cutoff"]:
                direction = 1 if observed_change > 0 else -1
                net_ret = (direction * pct_change * self.brain.params["leverage"]) - self.brain.params["fee"]
                self.capital *= (1 + net_ret)
                action = "long" if direction > 0 else "short"
                self.brain.record_action(action, net_ret)
                self.trade_history.append({
                    "index": i,
                    "action": action,
                    "price": float(prices[i]),
                    "next_price": float(prices[i + 1]),
                    "signal_change": float(observed_change),
                    "roi": float(net_ret),
                    "capital": float(self.capital),
                })

        return float(self.capital)

    def metrics(self):
        return {
            "capital": float(self.capital),
            "trades": len(self.trade_history),
            "trade_history": self.trade_history,
            "brain_summary": self.brain.summarize(),
        }
