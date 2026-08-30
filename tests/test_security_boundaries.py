import math
import unittest

from backend.hft_brain import CMSProductionHFTBot
from backend.modules.strategy_manager import StrategyManager
from backend.risk_management import RiskManager


class SecurityBoundaryTests(unittest.TestCase):
    def test_risk_rejects_non_finite_values(self):
        risk = RiskManager()
        self.assertFalse(risk.decide(math.nan, 1.0).allowed)
        self.assertFalse(risk.decide(100.0, math.inf).allowed)

    def test_strategy_rejects_non_finite_inputs(self):
        manager = StrategyManager()
        with self.assertRaises(ValueError):
            manager.execute(math.nan, 1.0, 100.0)
        with self.assertRaises(ValueError):
            manager.execute(1.0, 1.0, 0.0)

    def test_strategy_enforces_risk_leverage_ceiling(self):
        manager = StrategyManager()
        manager.config["leverage"] = 500.0
        with self.assertRaises(ValueError):
            manager.execute(0.1, 0.2, 100.0)
        manager.config["leverage"] = 200.0
        result = manager.execute(0.1, 0.2, 100.0)
        self.assertEqual(result["leverage"], 200.0)

    def test_strategy_accepts_explicit_margin_futures_leverage(self):
        manager = StrategyManager()
        result = manager.execute(0.1, 0.2, 100.0, leverage=10.0)
        self.assertEqual(result["leverage"], 10.0)
        with self.assertRaises(ValueError):
            manager.execute(0.1, 0.2, 100.0, leverage=300.0)
        with self.assertRaises(ValueError):
            manager.execute(0.1, 0.2, 100.0, leverage=0.0)

    def test_hft_rejects_invalid_and_oversized_input(self):
        bot = CMSProductionHFTBot()
        with self.assertRaises(ValueError):
            bot.trade_loop([100.0, math.nan, 101.0], [0.5, 0.5, 0.5])
        with self.assertRaises(ValueError):
            bot.trade_loop([100.0] * 5001, [0.5] * 5001)

    def test_hft_rejects_non_positive_prices(self):
        bot = CMSProductionHFTBot()
        with self.assertRaises(ValueError):
            bot.trade_loop([100.0, 0.0, 101.0], [0.5, 0.5, 0.5])


if __name__ == "__main__":
    unittest.main()
