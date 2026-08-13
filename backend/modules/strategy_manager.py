import yaml
from pathlib import Path
from .daily_harvester import DailyCompoundHarvesterModule, HarvesterStrategy

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

    def execute(self, news_sentiment: float, price_change: float, current_balance: float,
                fee_rate: float | None = None) -> dict:
        strategy = self.current_strategy()
        leverage = float(self.config.get("leverage", 1.5))
        fee_rate = float(self.config.get("fee_rate", 0.001) if fee_rate is None else fee_rate)
        if fee_rate < 0:
            raise ValueError("Комиссия не может быть отрицательной.")

        if strategy == HarvesterStrategy.PURE.value:
            next_balance, signal = self.module.process_tick(news_sentiment, price_change, current_balance, leverage)
        elif strategy == HarvesterStrategy.HFT_MOMENTUM.value:
            next_balance, signal = self.module.process_high_frequency(news_sentiment, price_change, current_balance, leverage)
        elif strategy == HarvesterStrategy.COMPOUND_DEFENDER.value:
            next_balance, signal = self.module.process_defender(news_sentiment, price_change, current_balance, leverage)
        else:
            next_balance, signal = self.module.process_tick(news_sentiment, price_change, current_balance, leverage)

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
            "leverage": leverage
        }
