import math
from pathlib import Path

import yaml

from .daily_harvester import DailyCompoundHarvesterModule, HarvesterStrategy


MAX_LEVERAGE = 2.0


class StrategyManager:
    def __init__(self, config_path: str = "backend/config.yaml"):
        configured_path = Path(config_path)
        self.config_path = (
            configured_path
            if configured_path.is_absolute()
            else Path(__file__).resolve().parents[2] / configured_path
        )
        self.config = self.load_config()
        self.module = DailyCompoundHarvesterModule()

    def load_config(self) -> dict:
        if not self.config_path.exists():
            return {"strategy": HarvesterStrategy.PURE.value, "leverage": 1.5}
        with self.config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def current_strategy(self) -> str:
        return self.config.get("strategy", HarvesterStrategy.PURE.value)

    def execute(
        self,
        news_sentiment: float,
        price_change: float,
        current_balance: float,
        fee_rate: float | None = None,
    ) -> dict:
        values = (news_sentiment, price_change, current_balance)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Входные значения стратегии должны быть конечными числами.")
        if current_balance <= 0:
            raise ValueError("Текущий баланс должен быть положительным.")

        strategy = self.current_strategy()
        leverage = float(self.config.get("leverage", 1.5))
        if not math.isfinite(leverage) or leverage <= 0 or leverage > MAX_LEVERAGE:
            raise ValueError("Плечо должно быть конечным, положительным и не превышать 2x.")

        fee_rate = float(self.config.get("fee_rate", 0.001) if fee_rate is None else fee_rate)
        if not math.isfinite(fee_rate) or fee_rate < 0 or fee_rate > 0.05:
            raise ValueError("Комиссия должна быть конечной и находиться в диапазоне 0..5%.")

        strategy_handlers = {
            HarvesterStrategy.PURE.value: lambda: self.module.process_tick(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.HFT_MOMENTUM.value: lambda: self.module.process_high_frequency(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.COMPOUND_DEFENDER.value: lambda: self.module.process_defender(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.TREND_BREAKOUT.value: lambda: self.module.process_trend_breakout(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.MULTI_SENTIMENT_SCALPER.value: lambda: self.module.process_multi_sentiment(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.AI_ADAPTIVE.value: lambda: self.module.process_ai_adaptive(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.QUANTUM_GRID.value: lambda: self.module.process_quantum_grid(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.NEURAL_PATTERN.value: lambda: self.module.process_neural_pattern(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.DELTA_NEUTRAL.value: lambda: self.module.process_delta_neutral(news_sentiment, price_change, current_balance, leverage),
            HarvesterStrategy.VOLATILITY_HARVEST.value: lambda: self.module.process_volatility_harvest(news_sentiment, price_change, current_balance, leverage),
        }

        handler = strategy_handlers.get(strategy, strategy_handlers[HarvesterStrategy.PURE.value])
        next_balance, signal = handler()

        if not math.isfinite(next_balance):
            raise ValueError("Стратегия вернула некорректный баланс.")

        fee = current_balance * leverage * fee_rate * 2
        net_balance = max(0.0, next_balance - fee)
        return {
            "strategy": strategy,
            "previous_balance": current_balance,
            "gross_next_balance": next_balance,
            "next_balance": net_balance,
            "fee_rate": fee_rate,
            "fee": fee,
            "pnl": net_balance - current_balance,
            "signal": signal,
            "leverage": leverage,
        }
