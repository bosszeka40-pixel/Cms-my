"""
Auto-strategy generator for the bot.
Generates parameter variations, backtests them, and publishes winners to marketplace.
"""
import random
import math
from datetime import datetime, timezone
from enum import Enum


class SignalMode(str, Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    GRID = "grid"
    ADAPTIVE = "adaptive"
    COMBINED = "combined"
    DELTA_NEUTRAL = "delta_neutral"


STRATEGY_TEMPLATES = [
    {"signal": "momentum", "leverage_range": (1.0, 2.0), "threshold_range": (0.005, 0.03), "hold_bars": (1, 3)},
    {"signal": "mean_reversion", "leverage_range": (0.8, 1.5), "threshold_range": (0.01, 0.05), "hold_bars": (2, 5)},
    {"signal": "breakout", "leverage_range": (1.2, 2.0), "threshold_range": (0.02, 0.06), "hold_bars": (1, 2)},
    {"signal": "scalping", "leverage_range": (1.5, 2.0), "threshold_range": (0.003, 0.015), "hold_bars": (1, 1)},
    {"signal": "grid", "leverage_range": (1.0, 1.8), "threshold_range": (0.01, 0.04), "hold_bars": (1, 3)},
    {"signal": "adaptive", "leverage_range": (1.0, 2.0), "threshold_range": (0.005, 0.04), "hold_bars": (1, 4)},
    {"signal": "combined", "leverage_range": (1.2, 2.0), "threshold_range": (0.01, 0.03), "hold_bars": (1, 3)},
    {"signal": "delta_neutral", "leverage_range": (0.8, 1.2), "threshold_range": (0.005, 0.02), "hold_bars": (2, 5)},
]

SIGNATURE_NAMES = {
    "momentum": ["Форсаж", "Рывок", "Импульс", "Стремительный"],
    "mean_reversion": ["Отскок", "Возврат", "Равновесие", "Контртренд"],
    "breakout": ["Прорыв", "Брейкаут", "Пробой", "Стена"],
    "scalping": ["Скальп", "Микро", "Тик", "Стрелок"],
    "grid": ["Сетка", "Грид", "Пattern", "Матрица"],
    "adaptive": ["Адаптив", "Эволюция", "Нейро", "ИИ"],
    "combined": ["Комбо", "Гибрид", "Фьюжн", "Синтез"],
    "delta_neutral": ["Дельта", "Баланс", "Хедж", "Стабильный"],
}

SUFFIXES = ["Pro", "Elite", "Alpha", "Beta", "Max", "Ultra", "Prime", "Turbo"]


def _generate_name(signal: str, index: int) -> str:
    base = random.choice(SIGNATURE_NAMES.get(signal, ["Стратегия"]))
    suffix = random.choice(SUFFIXES)
    return f"{base} {suffix} #{index}"


def _generate_description(signal: str, params: dict) -> str:
    descriptions = {
        "momentum": f"Следование за трендом с порогом {params['threshold']:.3f}. Леверидж {params['leverage']:.1f}x.",
        "mean_reversion": f"Возврат к среднему при отклонении {params['threshold']:.3f}. Безопасный подход.",
        "breakout": f"Прорыв уровня {params['threshold']:.3f} с усиленным левериджем {params['leverage']:.1f}x.",
        "scalping": f"Быстрые сделки с минимальным порогом {params['threshold']:.4f}. Высокая частота.",
        "grid": f"Сеточная торговля с ячейкой {params['threshold']:.3f}. Стабильный доход.",
        "adaptive": f"Адаптивный порог {params['threshold']:.3f}, подстраивается под рынок.",
        "combined": f"Комбинированный сигнал с фильтром {params['threshold']:.3f}. Универсальный.",
        "delta_neutral": f"Дельта-нейтральная позиция. Минимальный риск, стабильный доход.",
    }
    return descriptions.get(signal, f"Автоматически сгенерированная стратегия. Порог: {params['threshold']:.3f}.")


def _backtest_strategy(params: dict, candles: list[dict]) -> dict:
    """Backtest generated strategy parameters on real candles."""
    balance = 100.0
    trades = 0
    wins = 0
    returns = []
    peak = 100.0
    max_drawdown = 0.0
    leverage = params["leverage"]
    threshold = params["threshold"]
    signal_mode = params["signal"]
    hold_bars = params.get("hold_bars", 1)
    fee_rate = 0.001

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

        # Generate signal based on mode
        if signal_mode == "momentum":
            signal = 1 if previous_change > threshold else (-1 if previous_change < -threshold else 0)
        elif signal_mode == "mean_reversion":
            signal = -1 if previous_change > threshold else (1 if previous_change < -threshold else 0)
        elif signal_mode == "breakout":
            signal = 1 if abs(previous_change) > threshold else 0
        elif signal_mode == "scalping":
            signal = 1 if previous_change > threshold else (-1 if previous_change < -threshold else 0)
        elif signal_mode == "grid":
            signal = 1 if previous_change > 0 else -1
        elif signal_mode == "adaptive":
            adaptive_threshold = threshold * (1.0 + abs(previous_change) * 5)
            signal = 1 if previous_change > adaptive_threshold else (-1 if previous_change < -adaptive_threshold else 0)
        elif signal_mode == "combined":
            combined = previous_change * 0.6 + (1 if previous_change > 0 else -1) * threshold * 0.4
            signal = 1 if combined > threshold else (-1 if combined < -threshold else 0)
        elif signal_mode == "delta_neutral":
            signal = 1 if previous_change < 0 else -1
        else:
            signal = 1 if previous_change > 0 else -1

        if signal == 0:
            continue

        trade_return = signal * ((current_close - previous_close) / previous_close) * leverage
        net_return = trade_return - fee_rate
        balance = max(0.0, balance * (1 + net_return))
        returns.append(net_return)
        peak = max(peak, balance)
        max_drawdown = max(max_drawdown, (peak - balance) / peak if peak else 0.0)
        trades += 1
        wins += net_return > 0

    monthly_return = (balance / 100.0 - 1) * 100
    mean_return = sum(returns) / len(returns) if returns else 0.0
    variance = sum((v - mean_return) ** 2 for v in returns) / len(returns) if returns else 0.0
    volatility = math.sqrt(variance)
    sharpe = mean_return / volatility * math.sqrt(len(returns)) if volatility else 0.0
    gross_profit = sum(v for v in returns if v > 0)
    gross_loss = abs(sum(v for v in returns if v < 0))

    return {
        "monthly_return_pct": round(monthly_return, 2),
        "final_balance": round(balance, 2),
        "trades": trades,
        "win_rate": round(wins / trades * 100, 2) if trades else 0.0,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "sharpe": round(sharpe, 4),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else None,
    }


class StrategyGenerator:
    def __init__(self):
        self.generated_count = 0
        self.published_count = 0
        self.generation_log = []
        self.last_generation = None

    def generate_and_test(self, candles: list[dict], count: int = 5) -> list[dict]:
        """Generate random strategy variations, backtest, return candidates."""
        if not candles or len(candles) < 10:
            return []

        candidates = []
        for _ in range(count):
            template = random.choice(STRATEGY_TEMPLATES)
            params = {
                "signal": template["signal"],
                "leverage": round(random.uniform(*template["leverage_range"]), 2),
                "threshold": round(random.uniform(*template["threshold_range"]), 4),
                "hold_bars": random.randint(*template["hold_bars"]),
            }
            result = _backtest_strategy(params, candles)
            name = _generate_name(params["signal"], self.generated_count + 1)
            self.generated_count += 1

            candidates.append({
                "name": name,
                "description": _generate_description(params["signal"], params),
                "params": params,
                "result": result,
            })

        return candidates

    def select_winners(self, candidates: list[dict], min_return: float = 5.0,
                       min_win_rate: float = 45.0, max_drawdown: float = 30.0) -> list[dict]:
        """Filter candidates that meet quality criteria."""
        winners = []
        for c in candidates:
            r = c["result"]
            if (r["monthly_return_pct"] >= min_return and
                r["win_rate"] >= min_win_rate and
                r["max_drawdown_pct"] <= max_drawdown and
                r["trades"] >= 5):
                winners.append(c)
        return sorted(winners, key=lambda x: x["result"]["monthly_return_pct"], reverse=True)

    def publish_to_marketplace(self, engine, winners: list[dict]) -> list[dict]:
        """Publish winning strategies to the marketplace with 15-day free trial."""
        published = []
        for w in winners[:3]:  # Max 3 per generation round
            try:
                from sqlalchemy.orm import sessionmaker
                from ..cms_core import Plugin, Base
                session = engine.SessionLocal()
                try:
                    plugin_name = f"bot_{w['name'].lower().replace(' ', '_').replace('#', '')}"
                    existing = session.query(Plugin).filter(Plugin.name == plugin_name).first()
                    if not existing:
                        session.add(Plugin(name=plugin_name, price=0.0, description=w["description"]))
                        session.commit()
                        self.published_count += 1
                        published.append({"name": w["name"], "plugin_name": plugin_name, "return": w["result"]["monthly_return_pct"]})
                        self.generation_log.append({
                            "time": datetime.now(timezone.utc).isoformat(),
                            "name": w["name"],
                            "return": w["result"]["monthly_return_pct"],
                            "win_rate": w["result"]["win_rate"],
                            "action": "published",
                        })
                finally:
                    session.close()
            except Exception:
                continue
        return published

    def run_generation_cycle(self, engine, candles: list[dict]) -> dict:
        """Full cycle: generate, test, filter, publish."""
        self.last_generation = datetime.now(timezone.utc).isoformat()
        candidates = self.generate_and_test(candles, count=8)
        winners = self.select_winners(candidates)
        published = self.publish_to_marketplace(engine, winners)

        event = {
            "time": self.last_generation,
            "candidates": len(candidates),
            "winners": len(winners),
            "published": len(published),
            "best_return": winners[0]["result"]["monthly_return_pct"] if winners else 0,
        }
        self.generation_log.append(event)

        return {
            "generated": len(candidates),
            "winners": len(winners),
            "published": len(published),
            "candidates": [{"name": c["name"], "return": c["result"]["monthly_return_pct"],
                           "win_rate": c["result"]["win_rate"], "drawdown": c["result"]["max_drawdown_pct"]}
                          for c in candidates],
            "winner_details": [{"name": w["name"], "return": w["result"]["monthly_return_pct"],
                               "win_rate": w["result"]["win_rate"], "params": w["params"]}
                              for w in winners],
            "published_strategies": published,
        }

    def get_status(self) -> dict:
        return {
            "generated_count": self.generated_count,
            "published_count": self.published_count,
            "last_generation": self.last_generation,
            "recent_log": self.generation_log[-10:],
        }
