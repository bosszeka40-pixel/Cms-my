from datetime import datetime

class HFTBot:
    def __init__(self):
        self.active = False
        self.stats = []

    def start(self):
        self.active = True
        self.stats.append({"event": "started", "time": datetime.utcnow().isoformat()})
        return {"status": "started"}

    def stop(self):
        self.active = False
        self.stats.append({"event": "stopped", "time": datetime.utcnow().isoformat()})
        return {"status": "stopped"}

    def status(self):
        return {"active": self.active, "runs": len(self.stats), "stats": self.stats}

    def simulate_trade(self):
        trade = {"time": datetime.utcnow().isoformat(), "result": "simulated", "pl": 0.0}
        self.stats.append(trade)
        return trade

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
