from datetime import datetime
from collections import deque

from .trading_execution_gate import TradingExecutionGate


class HFTBot:
    def __init__(self):
        self.active = False
        self.stats = []
        self.execution_gate = TradingExecutionGate()
        self.memory = deque(maxlen=100)
        self.learning_data = []
        self.current_strategy = None
        self.last_signal = None
        self.trade_count = 0
        self.win_count = 0
        self.total_pnl = 0.0
        self.current_balance = 100.0
        self.activity_log = deque(maxlen=50)

    def start(self):
        self.active = True
        event = {"event": "started", "time": datetime.utcnow().isoformat(), "detail": "Бот запущен и готов к работе"}
        self.stats.append(event)
        self.activity_log.append(event)
        return {"status": "started"}

    def stop(self):
        self.active = False
        event = {"event": "stopped", "time": datetime.utcnow().isoformat(), "detail": "Бот остановлен"}
        self.stats.append(event)
        self.activity_log.append(event)
        return {"status": "stopped"}

    def status(self):
        return {
            "active": self.active,
            "runs": len(self.stats),
            "stats": self.stats,
            "execution": self.execution_gate.status(),
            "memory_count": len(self.memory),
            "learning_samples": len(self.learning_data),
            "trade_count": self.trade_count,
            "win_count": self.win_count,
            "win_rate": round(self.win_count / max(1, self.trade_count) * 100, 1),
            "total_pnl": round(self.total_pnl, 4),
            "current_balance": round(self.current_balance, 2),
            "current_strategy": self.current_strategy,
            "last_signal": self.last_signal,
            "activity_log": list(self.activity_log)[-10:],
        }

    def simulate_trade(self):
        trade = {"time": datetime.utcnow().isoformat(), "result": "simulated", "pl": 0.0}
        self.stats.append(trade)
        self.activity_log.append(trade)
        return trade

    def execute_trade(self, balance, leverage, stop_loss_pct, notional):
        decision = self.execution_gate.check(
            balance=balance,
            leverage=leverage,
            stop_loss_pct=stop_loss_pct,
            notional=notional,
        )
        result = {
            "time": datetime.utcnow().isoformat(),
            "event": "execution_check",
            "allowed": decision.allowed,
            "reason": decision.reason,
        }
        self.stats.append(result)
        self.activity_log.append(result)
        return result

    def simulate(self, pair, strategy, result):
        trade = {
            "time": datetime.utcnow().isoformat(),
            "event": "test_trade",
            "pair": pair,
            "strategy": strategy,
            "signal": result["signal"],
            "previous_balance": result["previous_balance"],
            "next_balance": result["next_balance"],
            "pl": result["next_balance"] - result["previous_balance"],
        }
        self.stats.append(trade)
        self.activity_log.append(trade)
        self.trade_count += 1
        pnl = result["next_balance"] - result["previous_balance"]
        self.total_pnl += pnl
        self.current_balance = result["next_balance"]
        if pnl > 0:
            self.win_count += 1
        self.last_signal = {"pair": pair, "signal": result["signal"], "pnl": pnl, "time": trade["time"]}
        memory_entry = {
            "pair": pair,
            "strategy": strategy,
            "signal": result["signal"],
            "pnl": pnl,
            "balance": result["next_balance"],
            "time": trade["time"],
        }
        self.memory.append(memory_entry)
        self.learning_data.append({
            "strategy": strategy,
            "signal": result["signal"],
            "pnl": pnl,
            "balance": result["next_balance"],
        })
        return trade

    def get_memory_summary(self):
        if not self.memory:
            return {"total_trades": 0, "avg_pnl": 0, "best_trade": None, "worst_trade": None, "strategies_used": []}
        pnls = [m["pnl"] for m in self.memory]
        strategies = list(set(m["strategy"] for m in self.memory))
        return {
            "total_trades": len(self.memory),
            "avg_pnl": round(sum(pnls) / len(pnls), 4),
            "best_trade": max(self.memory, key=lambda x: x["pnl"]),
            "worst_trade": min(self.memory, key=lambda x: x["pnl"]),
            "strategies_used": strategies,
            "win_rate": round(self.win_count / max(1, self.trade_count) * 100, 1),
        }

    def set_strategy(self, strategy_name):
        self.current_strategy = strategy_name
        event = {"event": "strategy_changed", "time": datetime.utcnow().isoformat(), "detail": f"Стратегия: {strategy_name}"}
        self.activity_log.append(event)
        return {"status": "ok", "strategy": strategy_name}
