from enum import Enum

class HarvesterStrategy(str, Enum):
    PURE = "pure_harvester"
    HFT_MOMENTUM = "high_frequency_momentum"
    COMPOUND_DEFENDER = "compound_defender"
    TREND_BREAKOUT = "trend_breakout_compound"
    MULTI_SENTIMENT_SCALPER = "multi_sentiment_scalper"

class DailyCompoundHarvesterModule:
    def process_tick(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.5) -> tuple[float, int]:
        signal = 1 if (news_sentiment > 0 and price_change > 0) else -1
        trade_return = signal * price_change * leverage
        next_balance = current_balance * (1 + trade_return)
        return next_balance, signal

    def process_high_frequency(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 2.0) -> tuple[float, int]:
        signal = 1 if news_sentiment > 0 else -1
        trade_return = signal * price_change * leverage
        return current_balance * (1 + trade_return), signal

    def process_defender(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.0) -> tuple[float, int]:
        signal = -1 if price_change < 0 else 1
        trade_return = signal * price_change * leverage * 0.75
        return current_balance * (1 + trade_return), signal
