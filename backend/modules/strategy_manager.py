import yaml
from pathlib import Path
from .daily_harvester import DailyCompoundHarvesterModule, HarvesterStrategy

class StrategyManager:
    def __init__(self, config_path: str = "backend/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.module = DailyCompoundHarvesterModule()

    def load_config(self) -> dict:
        if not self.config_path.exists():
            return {"strategy": HarvesterStrategy.PURE.value, "leverage": 1.5}
        with self.config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def current_strategy(self) -> str:
        return self.config.get("strategy", HarvesterStrategy.PURE.value)

    def execute(self, news_sentiment: float, price_change: float, current_balance: float) -> dict:
        strategy = self.current_strategy()
        leverage = float(self.config.get("leverage", 1.5))

        if strategy == HarvesterStrategy.PURE.value:
            next_balance, signal = self.module.process_tick(news_sentiment, price_change, current_balance, leverage)
        elif strategy == HarvesterStrategy.HFT_MOMENTUM.value:
            next_balance, signal = self.module.process_high_frequency(news_sentiment, price_change, current_balance, leverage)
        elif strategy == HarvesterStrategy.COMPOUND_DEFENDER.value:
            next_balance, signal = self.module.process_defender(news_sentiment, price_change, current_balance, leverage)
        else:
            next_balance, signal = self.module.process_tick(news_sentiment, price_change, current_balance, leverage)

        return {
            "strategy": strategy,
            "previous_balance": current_balance,
            "next_balance": next_balance,
            "signal": signal,
            "leverage": leverage
        }
