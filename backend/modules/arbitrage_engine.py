"""
Arbitrage Engine — модуль арбитражных стратегий для CMS Trading Platform.
Триангулярный, межбиржевой, статистический и funding-rate арбитраж.
"""
import math
import time
from datetime import datetime, timezone
from collections import deque


class TriangularArbitrage:
    """Треугольный арбитраж: USDT → BTC → ETH → USDT на одной бирже."""

    def __init__(self):
        self.name = "Треугольный арбитраж"
        self.description = "Поиск прибыльных треугольников между тремя парами на одной бирже."
        self.opportunities = deque(maxlen=50)
        self.total_pnl = 0.0
        self.trade_count = 0
        self.win_count = 0

    def scan(self, tickers: dict) -> list[dict]:
        """Сканирует треугольники USDT→BTC→ETH→USDT и аналогичные."""
        triangles = [
            ("BTC/USDT", "ETH/BTC", "ETH/USDT", "long"),
            ("BTC/USDT", "ETH/BTC", "ETH/USDT", "short"),
            ("BNB/USDT", "ETH/BNB", "ETH/USDT", "long"),
            ("SOL/USDT", "ETH/SOL", "ETH/USDT", "long"),
            ("BTC/USDT", "SOL/BTC", "SOL/USDT", "long"),
        ]
        opportunities = []
        for pair1, pair2, pair3, direction in triangles:
            t1 = tickers.get(pair1)
            t2 = tickers.get(pair2)
            t3 = tickers.get(pair3)
            if not all([t1, t2, t3]):
                continue
            try:
                if direction == "long":
                    p1 = float(t1.get("ask", t1.get("last", 0)))
                    p2_ask = float(t2.get("ask", t2.get("last", 0)))
                    p3_bid = float(t3.get("bid", t3.get("last", 0)))
                    if p1 <= 0 or p2_ask <= 0 or p3_bid <= 0:
                        continue
                    usdt_to_btc = 1.0 / p1
                    btc_to_eth = usdt_to_btc * (1.0 / p2_ask)
                    eth_to_usdt = btc_to_eth * p3_bid
                    profit_pct = (eth_to_usdt - 1.0) * 100
                else:
                    p1_bid = float(t1.get("bid", t1.get("last", 0)))
                    p2 = float(t2.get("last", 0))
                    p3_ask = float(t3.get("ask", t3.get("last", 0)))
                    if p1_bid <= 0 or p2 <= 0 or p3_ask <= 0:
                        continue
                    usdt_to_eth = 1.0 / p3_ask
                    eth_to_btc = usdt_to_eth * p2
                    btc_to_usdt = eth_to_btc * p1_bid
                    profit_pct = (btc_to_usdt - 1.0) * 100

                fee = 0.1  # 0.1% round-trip
                net_profit = profit_pct - fee
                if net_profit > 0.01:
                    opp = {
                        "type": "triangular",
                        "direction": direction,
                        "pairs": [pair1, pair2, pair3],
                        "gross_profit_pct": round(profit_pct, 4),
                        "net_profit_pct": round(net_profit, 4),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    opportunities.append(opp)
                    self.opportunities.append(opp)
            except (ValueError, ZeroDivisionError, TypeError):
                continue
        return sorted(opportunities, key=lambda x: x["net_profit_pct"], reverse=True)

    def execute(self, amount_usdt: float, best_opp: dict) -> dict:
        if not best_opp or best_opp.get("net_profit_pct", 0) <= 0:
            return {"executed": False, "reason": "Нет прибыльных возможностей"}
        pnl = amount_usdt * best_opp["net_profit_pct"] / 100
        self.trade_count += 1
        self.total_pnl += pnl
        if pnl > 0:
            self.win_count += 1
        return {
            "executed": True,
            "pairs": best_opp["pairs"],
            "amount": amount_usdt,
            "pnl": round(pnl, 4),
            "new_balance": round(amount_usdt + pnl, 2),
            "profit_pct": best_opp["net_profit_pct"],
        }

    def status(self) -> dict:
        return {
            "name": self.name,
            "opportunities_found": len(self.opportunities),
            "trade_count": self.trade_count,
            "win_count": self.win_count,
            "win_rate": round(self.win_count / max(1, self.trade_count) * 100, 1),
            "total_pnl": round(self.total_pnl, 4),
            "recent": list(self.opportunities)[-5:],
        }


class CrossExchangeArbitrage:
    """Межбиржевой арбитраж: разница цен между двумя биржами."""

    def __init__(self):
        self.name = "Межбиржевой арбитраж"
        self.description = "Сравнение цен одной пары на разных биржах."
        self.opportunities = deque(maxlen=50)
        self.total_pnl = 0.0
        self.trade_count = 0
        self.win_count = 0

    def scan(self, ticker_exchange_a: dict, ticker_exchange_b: dict, pair: str = "BTC/USDT") -> dict | None:
        ta = ticker_exchange_a.get(pair)
        tb = ticker_exchange_b.get(pair)
        if not ta or not tb:
            return None
        try:
            ask_a = float(ta.get("ask", ta.get("last", 0)))
            bid_b = float(tb.get("bid", tb.get("last", 0)))
            ask_b = float(tb.get("ask", tb.get("last", 0)))
            bid_a = float(ta.get("bid", ta.get("last", 0)))
            if ask_a <= 0 or bid_b <= 0:
                return None
            spread_ab = (bid_b - ask_a) / ask_a * 100
            spread_ba = (bid_a - ask_b) / ask_b * 100
            fee = 0.2
            best = None
            if spread_ab - fee > 0:
                best = {"direction": "A→B", "pair": pair, "spread_pct": round(spread_ab, 4), "net_pct": round(spread_ab - fee, 4), "ask_a": ask_a, "bid_b": bid_b}
            if spread_ba - fee > 0 and (not best or spread_ba - fee > best["net_pct"]):
                best = {"direction": "B→A", "pair": pair, "spread_pct": round(spread_ba, 4), "net_pct": round(spread_ba - fee, 4), "ask_b": ask_b, "bid_a": bid_a}
            if best:
                best["type"] = "cross_exchange"
                best["timestamp"] = datetime.now(timezone.utc).isoformat()
                self.opportunities.append(best)
            return best
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def execute(self, amount: float, opp: dict) -> dict:
        if not opp or opp.get("net_pct", 0) <= 0:
            return {"executed": False, "reason": "Нет прибыльного спреда"}
        pnl = amount * opp["net_pct"] / 100
        self.trade_count += 1
        self.total_pnl += pnl
        if pnl > 0:
            self.win_count += 1
        return {"executed": True, "pnl": round(pnl, 4), "new_balance": round(amount + pnl, 2), **opp}

    def status(self) -> dict:
        return {
            "name": self.name,
            "opportunities_found": len(self.opportunities),
            "trade_count": self.trade_count,
            "win_rate": round(self.win_count / max(1, self.trade_count) * 100, 1),
            "total_pnl": round(self.total_pnl, 4),
            "recent": list(self.opportunities)[-5:],
        }


class StatisticalArbitrage:
    """Статистический арбитраж: поиск ценовых отклонений от среднего."""

    def __init__(self, lookback: int = 100):
        self.name = "Статистический арбитраж"
        self.description = "Z-score анализ для поиска отклонений от средней цены."
        self.lookback = lookback
        self.prices: dict[str, list[float]] = {}
        self.opportunities = deque(maxlen=50)
        self.total_pnl = 0.0
        self.trade_count = 0
        self.win_count = 0

    def update(self, pair: str, price: float):
        if pair not in self.prices:
            self.prices[pair] = []
        self.prices[pair].append(price)
        if len(self.prices[pair]) > self.lookback:
            self.prices[pair] = self.prices[pair][-self.lookback:]

    def scan(self, pair: str, current_price: float, z_threshold: float = 2.0) -> dict | None:
        self.update(pair, current_price)
        prices = self.prices.get(pair, [])
        if len(prices) < 20:
            return None
        try:
            mean = sum(prices) / len(prices)
            variance = sum((p - mean) ** 2 for p in prices) / len(prices)
            std = math.sqrt(variance) if variance > 0 else 0.001
            z_score = (current_price - mean) / std
            if abs(z_score) > z_threshold:
                signal = "short" if z_score > 0 else "long"
                opp = {
                    "type": "statistical",
                    "pair": pair,
                    "signal": signal,
                    "z_score": round(z_score, 4),
                    "mean": round(mean, 4),
                    "current": round(current_price, 4),
                    "deviation_pct": round(abs(current_price - mean) / mean * 100, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self.opportunities.append(opp)
                return opp
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        return None

    def execute(self, amount: float, opp: dict) -> dict:
        if not opp:
            return {"executed": False}
        deviation = opp.get("deviation_pct", 0)
        pnl = amount * deviation / 100 * 0.5
        self.trade_count += 1
        self.total_pnl += pnl
        if pnl > 0:
            self.win_count += 1
        return {"executed": True, "pnl": round(pnl, 4), "new_balance": round(amount + pnl, 2), **opp}

    def status(self) -> dict:
        return {
            "name": self.name,
            "pairs_tracked": len(self.prices),
            "opportunities_found": len(self.opportunities),
            "trade_count": self.trade_count,
            "win_rate": round(self.win_count / max(1, self.trade_count) * 100, 1),
            "total_pnl": round(self.total_pnl, 4),
            "recent": list(self.opportunities)[-5:],
        }


class FundingRateArbitrage:
    """Funding-rate арбитраж: заработок на funding между спотом и деривативами."""

    def __init__(self):
        self.name = "Funding Rate арбитраж"
        self.description = "Заем funding между спотом и фьючерсами."
        self.opportunities = deque(maxlen=50)
        self.total_pnl = 0.0
        self.trade_count = 0
        self.win_count = 0

    def scan(self, funding_rates: dict) -> list[dict]:
        opportunities = []
        for pair, rate_data in funding_rates.items():
            try:
                rate = float(rate_data.get("rate", 0))
                if abs(rate) > 0.0001:
                    annualized = rate * 3 * 365 * 100
                    signal = "short_funding" if rate > 0 else "long_funding"
                    opp = {
                        "type": "funding_rate",
                        "pair": pair,
                        "signal": signal,
                        "funding_rate": round(rate, 8),
                        "annualized_pct": round(annualized, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    opportunities.append(opp)
                    self.opportunities.append(opp)
            except (ValueError, TypeError):
                continue
        return sorted(opportunities, key=lambda x: abs(x["annualized_pct"]), reverse=True)

    def execute(self, amount: float, opp: dict) -> dict:
        if not opp:
            return {"executed": False}
        daily_pnl = amount * opp["funding_rate"]
        self.trade_count += 1
        self.total_pnl += daily_pnl
        if daily_pnl > 0:
            self.win_count += 1
        return {"executed": True, "pnl": round(daily_pnl, 4), "new_balance": round(amount + daily_pnl, 2), **opp}

    def status(self) -> dict:
        return {
            "name": self.name,
            "opportunities_found": len(self.opportunities),
            "trade_count": self.trade_count,
            "win_rate": round(self.win_count / max(1, self.trade_count) * 100, 1),
            "total_pnl": round(self.total_pnl, 4),
            "recent": list(self.opportunities)[-5:],
        }


class ArbitrageEngine:
    """Главный арбитражный движок — объединяет все типы арбитража."""

    def __init__(self):
        self.triangular = TriangularArbitrage()
        self.cross_exchange = CrossExchangeArbitrage()
        self.statistical = StatisticalArbitrage()
        self.funding_rate = FundingRateArbitrage()
        self.total_pnl = 0.0
        self.total_trades = 0
        self.active = False

    def start(self):
        self.active = True
        return {"status": "started"}

    def stop(self):
        self.active = False
        return {"status": "stopped"}

    def scan_all(self, tickers: dict = None, funding_rates: dict = None) -> dict:
        results = {}
        if tickers:
            results["triangular"] = self.triangular.scan(tickers)
        if funding_rates:
            results["funding_rate"] = self.funding_rate.scan(funding_rates)
        return results

    def status(self) -> dict:
        return {
            "active": self.active,
            "total_pnl": round(self.triangular.total_pnl + self.cross_exchange.total_pnl + self.statistical.total_pnl + self.funding_rate.total_pnl, 4),
            "total_trades": self.triangular.trade_count + self.cross_exchange.trade_count + self.statistical.trade_count + self.funding_rate.trade_count,
            "modules": {
                "triangular": self.triangular.status(),
                "cross_exchange": self.cross_exchange.status(),
                "statistical": self.statistical.status(),
                "funding_rate": self.funding_rate.status(),
            },
        }
