from datetime import datetime, timezone
import math


INITIAL_BALANCE_EUR = 100.0
TRADING_FEE_RATE = 0.001
LICENSE_DURATIONS_DAYS = (1, 3, 7, 14, 15, 30)


def price_for_duration(price_eur: float, duration_days: int) -> float:
    if duration_days not in LICENSE_DURATIONS_DAYS:
        raise ValueError("Срок должен быть 1, 3, 7, 14, 15 или 30 дней.")
    if price_eur <= 0:
        return 0.0
    return round(max(0.01, price_eur * duration_days / 15), 2)


def pricing_for_return(monthly_return_pct: float) -> tuple[str, float]:
    """Return a transparent category and 15-day euro price for a monthly result."""
    if monthly_return_pct < 0:
        return "Неудачные", 0.0
    if monthly_return_pct < 5:
        return "Безубыточные", 0.0
    if monthly_return_pct < 15:
        return "Стабильные", 1.0
    if monthly_return_pct < 30:
        return "Прибыльные", 1.5
    if monthly_return_pct < 50:
        return "Высокоприбыльные", 2.25
    if monthly_return_pct < 100:
        return "Очень прибыльные", 5.0
    return "Исключительно прибыльные", 10.0


def _signal(strategy: str, previous_change: float) -> int:
    if strategy in {"compound_defender", "trend_breakout_compound"}:
        return -1 if previous_change > 0 else 1
    return 1 if previous_change > 0 else -1


def evaluate_strategy(strategy: str, candles: list[dict]) -> dict:
    """Backtest one strategy using only the preceding closed daily candle."""
    balance = INITIAL_BALANCE_EUR
    trades = 0
    wins = 0
    returns = []
    peak = INITIAL_BALANCE_EUR
    max_drawdown = 0.0
    for index in range(1, len(candles)):
        previous_close = float(candles[index - 1]["close"])
        current_close = float(candles[index]["close"])
        if previous_close <= 0:
            continue
        previous_change = (
            (previous_close - float(candles[index - 2]["close"]))
            / float(candles[index - 2]["close"])
            if index > 1 and float(candles[index - 2]["close"]) > 0
            else 0.0
        )
        signal = _signal(strategy, previous_change)
        trade_return = signal * ((current_close - previous_close) / previous_close)
        net_return = trade_return - TRADING_FEE_RATE
        balance = max(0.0, balance * (1 + net_return))
        returns.append(net_return)
        peak = max(peak, balance)
        max_drawdown = max(max_drawdown, (peak - balance) / peak if peak else 0.0)
        trades += 1
        wins += net_return > 0
    monthly_return = (balance / INITIAL_BALANCE_EUR - 1) * 100
    category, price = pricing_for_return(monthly_return)
    mean_return = sum(returns) / len(returns) if returns else 0.0
    variance = (
        sum((value - mean_return) ** 2 for value in returns) / len(returns)
        if returns else 0.0
    )
    downside = [min(0.0, value) for value in returns]
    downside_deviation = math.sqrt(sum(value * value for value in downside) / len(returns)) if returns else 0.0
    volatility = math.sqrt(variance)
    sharpe = mean_return / volatility * math.sqrt(len(returns)) if volatility else 0.0
    sortino = mean_return / downside_deviation * math.sqrt(len(returns)) if downside_deviation else 0.0
    gross_profit = sum(value for value in returns if value > 0)
    gross_loss = abs(sum(value for value in returns if value < 0))
    return {
        "initial_balance_eur": INITIAL_BALANCE_EUR,
        "final_balance_eur": round(balance, 2),
        "monthly_return_pct": round(monthly_return, 2),
        "category": category,
        "price_eur": price,
        "access_days": 15 if price else None,
        "trades": trades,
        "win_rate_pct": round(wins / trades * 100, 2) if trades else 0.0,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else None,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "data_source": "real closed daily OHLCV candles",
        "data_days": len(candles),
    }


def evaluate_strategies(candles: list[dict], strategy_names: list[str]) -> dict[str, dict]:
    return {name: evaluate_strategy(name, candles) for name in strategy_names}
