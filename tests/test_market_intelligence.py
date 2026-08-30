"""Тесты: реальные стаканы, фичи графика и онлайн-обучение бота."""

import math
import tempfile
import unittest
from pathlib import Path

from backend.modules.market_features import (
    candle_features, feature_vector, heuristic_sentiment, rsi, ema,
)
from backend.modules.order_book import _normalize, depth_features
from backend.modules.bot_learner import OnlineSignalLearner


def make_candles(n=40, base=60000.0, drift=0.001, seed=7):
    r = dict(seed=seed)
    out = []
    price = base
    for i in range(n):
        r["seed"] = (r["seed"] * 1103515245 + 12345) & 0x7FFFFFFF
        noise = (r["seed"] / 0x7FFFFFFF - 0.5) * 2
        price *= 1 + drift + noise * 0.002
        out.append([1_600_000_000 + i * 3_600_000, price, price * 1.001, price * 0.999, price, 1000 + i])
    return out


class OrderBookTests(unittest.TestCase):
    def test_normalize_and_features(self):
        raw = {
            "timestamp": 1700000000000,
            "bids": [[50000.0, 1.0], [49999.0, 2.0], [49998.0, 0.5]],
            "asks": [[50001.0, 1.5], [50002.0, 0.5], [50003.0, 3.0]],
        }
        sn = _normalize(raw, 10)
        self.assertEqual(sn["best_bid"], 50000.0)
        self.assertEqual(sn["best_ask"], 50001.0)
        self.assertAlmostEqual(sn["spread"], 1.0)
        self.assertAlmostEqual(sn["mid"], 50000.5)
        metrics = depth_features(sn)
        self.assertGreaterEqual(metrics["imbalance"], -1.0)
        self.assertLessEqual(metrics["imbalance"], 1.0)
        self.assertGreater(metrics["spread_pct"], 0.0)
        self.assertAlmostEqual(metrics["bid_side_pct"], 3.5 / 8.5 * 100, places=4)

    def test_empty_book(self):
        sn = _normalize({"bids": [], "asks": []}, 5)
        self.assertIsNone(sn["best_bid"])
        self.assertIsNone(sn["spread"])
        metrics = depth_features(sn)
        self.assertEqual(metrics["imbalance"], 0.0)
        self.assertEqual(metrics["spread_pct"], 0.0)


class MarketFeaturesTests(unittest.TestCase):
    def test_rsi_bounds(self):
        candles = make_candles(40)
        closes = [float(c[4]) for c in candles]
        value = rsi(closes, 14)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 100.0)
        self.assertEqual(rsi([]), 50.0)

    def test_ema_monotonic(self):
        candles = make_candles(30)
        closes = [float(c[4]) for c in candles]
        self.assertGreater(ema(closes, 7), 0.0)
        self.assertGreater(ema(closes, 25), 0.0)

    def test_candle_features_keys(self):
        feat = candle_features(make_candles(20), make_candles(5))
        for key in ("momentum_1h", "momentum_4h", "rsi14", "vol_ratio", "ema_gap", "last_price"):
            self.assertIn(key, feat)
        self.assertEqual(candle_features([]), {})

    def test_feature_vector(self):
        candles = make_candles(20)
        depth = {"imbalance": 0.2, "spread_pct": 0.0001}
        vec = feature_vector(candle_features(candles), depth)
        self.assertEqual(len(vec), 8)
        for value in vec:
            self.assertGreaterEqual(value, -1.01)
            self.assertLessEqual(value, 1.01)
        self.assertIsNone(feature_vector({}, depth))

    def test_heuristic_sentiment_bounds(self):
        candles = make_candles(20)
        depth = {"imbalance": -0.3, "spread_pct": 0.0001}
        value = heuristic_sentiment(candle_features(candles), depth)
        self.assertGreaterEqual(value, -1.0)
        self.assertLessEqual(value, 1.0)
        self.assertEqual(heuristic_sentiment({}), 0.0)


class BotLearnerTests(unittest.TestCase):
    def test_predict_and_train_with_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "learning_state.json"
            learner = OnlineSignalLearner(state_path=state)
            vec = [0.5, 0.2, 0.1, 0.3, 0.4, -0.1, 0.6, -0.2]
            before = learner.predict_confidence(vec)
            self.assertGreaterEqual(before, 0.0)
            self.assertLessEqual(before, 1.0)
            learner.update(vec, 0.05)  # прибыльная сделка
            learner.update(vec, -0.03)
            after = learner.predict_confidence(vec)
            stats = learner.stats()
            self.assertEqual(stats["train_count"], 2)
            self.assertEqual(stats["wins"], 1)
            self.assertAlmostEqual(stats["win_rate"], 0.5)

            # перезагрузка из файла
            learner2 = OnlineSignalLearner(state_path=state)
            self.assertEqual(learner2.stats()["train_count"], 2)

    def test_update_ignores_nan_and_short_vectors(self):
        learner = OnlineSignalLearner(state_path=None)
        learner.update([0.1, "nan", 0.2, 0, 0, 0, 0, 0], 0.05)
        self.assertEqual(learner.stats()["train_count"], 0)
        learner.update([0.1, 0.2], 0.05)
        self.assertEqual(learner.stats()["train_count"], 0)

    def test_reset(self):
        learner = OnlineSignalLearner(state_path=None)
        learner.update([0.1] * 8, 0.05)
        learner.update([0.2] * 8, -0.05)
        learner.reset()
        stats = learner.stats()
        self.assertEqual(stats["train_count"], 0)
        self.assertIsNone(stats["win_rate"])

    def test_suggest_direction_cutoff(self):
        learner = OnlineSignalLearner(state_path=None, confidence_cutoff=0.62)
        self.assertEqual(learner.suggest_direction(0.9), 1)
        self.assertEqual(learner.suggest_direction(0.1), -1)
        self.assertEqual(learner.suggest_direction(0.5), 0)


if __name__ == "__main__":
    unittest.main()