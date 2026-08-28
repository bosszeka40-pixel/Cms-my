from enum import Enum

class HarvesterStrategy(str, Enum):
    PURE = "pure_harvester"
    HFT_MOMENTUM = "high_frequency_momentum"
    COMPOUND_DEFENDER = "compound_defender"
    TREND_BREAKOUT = "trend_breakout_compound"
    MULTI_SENTIMENT_SCALPER = "multi_sentiment_scalper"
    AI_ADAPTIVE = "ai_adaptive_momentum"
    QUANTUM_GRID = "quantum_grid_trader"
    NEURAL_PATTERN = "neural_pattern_recognition"
    DELTA_NEUTRAL = "delta_neutral_hedger"
    VOLATILITY_HARVEST = "volatility_harvest"

class DailyCompoundHarvesterModule:
    def process_tick(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.5) -> tuple[float, int]:
        signal = 1 if (news_sentiment > 0 and price_change > 0) else -1
        trade_return = signal * (price_change / 100) * leverage
        next_balance = current_balance * (1 + trade_return)
        return next_balance, signal

    def process_high_frequency(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 2.0) -> tuple[float, int]:
        signal = 1 if news_sentiment > 0 else -1
        trade_return = signal * (price_change / 100) * leverage
        return current_balance * (1 + trade_return), signal

    def process_defender(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.0) -> tuple[float, int]:
        signal = -1 if price_change < 0 else 1
        trade_return = signal * (price_change / 100) * leverage * 0.75
        return current_balance * (1 + trade_return), signal

    def process_trend_breakout(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.8) -> tuple[float, int]:
        signal = -1 if price_change > 0 else 1
        trade_return = signal * (price_change / 100) * leverage * 1.2
        return current_balance * (1 + trade_return), signal

    def process_multi_sentiment(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 2.0) -> tuple[float, int]:
        combined = (news_sentiment + (price_change / 10)) / 2
        signal = 1 if combined > 0.1 else (-1 if combined < -0.1 else 0)
        trade_return = signal * (price_change / 100) * leverage
        return current_balance * (1 + trade_return), signal

    def process_ai_adaptive(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.5) -> tuple[float, int]:
        adaptive_threshold = 0.01 * (current_balance / 100)
        signal = 1 if price_change > adaptive_threshold else (-1 if price_change < -adaptive_threshold else 0)
        trade_return = signal * (price_change / 100) * leverage * (1 + abs(news_sentiment) * 0.3)
        return current_balance * (1 + trade_return), signal

    def process_quantum_grid(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.2) -> tuple[float, int]:
        signal = 1 if price_change > 0 else -1
        grid_factor = 1.0 + (abs(news_sentiment) * 0.2)
        trade_return = signal * (price_change / 100) * leverage * grid_factor
        return current_balance * (1 + trade_return), signal

    def process_neural_pattern(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.5) -> tuple[float, int]:
        pattern_score = news_sentiment * 0.6 + (price_change / 10) * 0.4
        signal = 1 if pattern_score > 0.05 else (-1 if pattern_score < -0.05 else 0)
        trade_return = signal * (price_change / 100) * leverage
        return current_balance * (1 + trade_return), signal

    def process_delta_neutral(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.0) -> tuple[float, int]:
        signal = 1 if price_change < 0 else -1
        trade_return = signal * (price_change / 100) * leverage * 0.8
        return current_balance * (1 + trade_return), signal

    def process_volatility_harvest(self, news_sentiment: float, price_change: float, current_balance: float, leverage: float = 1.8) -> tuple[float, int]:
        signal = 1 if abs(price_change) > 2 else -1
        trade_return = signal * (price_change / 100) * leverage * 1.1
        return current_balance * (1 + trade_return), signal
