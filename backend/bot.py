from datetime import datetime

from .trading_execution_gate import TradingExecutionGate


class HFTBot:
    def __init__(self):
        self.active = False
        self.stats = []
        self.execution_gate = TradingExecutionGate()

    def start(self):
        self.active = True
        self.stats.append({"event": "started", "time": datetime.utcnow().isoformat()})
        return {"status": "started"}

    def stop(self):
        self.active = False
        self.stats.append({"event": "stopped", "time": datetime.utcnow().isoformat()})
        return {"status": "stopped"}

    def status(self):
        return {
            "active": self.active,
            "runs": len(self.stats),
            "stats": self.stats,
            "execution": self.execution_gate.status(),
        }

    def simulate_trade(self):
        trade = {"time": datetime.utcnow().isoformat(), "result": "simulated", "pl": 0.0}
        self.stats.append(trade)
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
        return trade
