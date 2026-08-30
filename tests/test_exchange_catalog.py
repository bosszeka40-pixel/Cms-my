import unittest

from backend.exchange_catalog import (
    EXCHANGE_CATALOG,
    MARKET_MODES,
    default_fee,
    effective_leverage,
    exchange_catalog,
    supports_mode,
)


class ExchangeCatalogTests(unittest.TestCase):
    def test_all_supported_exchanges_have_catalog_entries(self):
        for name in ("binance", "bybit", "kraken", "okx", "bitfinex", "pionex"):
            self.assertIn(name, EXCHANGE_CATALOG)

    def test_real_fees_not_zero_and_sane(self):
        for name, entry in EXCHANGE_CATALOG.items():
            self.assertGreater(entry["fees"]["taker"], 0)
            self.assertLess(entry["fees"]["taker"], 0.01)
            self.assertGreaterEqual(entry["fees"]["maker"], 0)

    def test_spot_leverage_always_capped_to_one(self):
        for name in EXCHANGE_CATALOG:
            self.assertEqual(effective_leverage(name, "spot", 100.0), 1.0)

    def test_binance_futures_leverage_and_fee(self):
        self.assertTrue(supports_mode("binance", "futures"))
        self.assertEqual(effective_leverage("binance", "futures", 500.0), 125.0)
        self.assertEqual(effective_leverage("binance", "futures", 10.0), 10.0)
        self.assertEqual(default_fee("binance", "futures"), 0.0005)
        self.assertEqual(default_fee("binance", "spot"), 0.001)

    def test_pionex_has_no_margin_or_futures(self):
        self.assertTrue(supports_mode("pionex", "spot"))
        self.assertFalse(supports_mode("pionex", "futures"))
        self.assertFalse(supports_mode("pionex", "margin_cross"))
        self.assertEqual(default_fee("pionex"), 0.0005)
        self.assertEqual(effective_leverage("pionex", "futures", 50.0), 1.0)

    def test_kraken_no_futures(self):
        self.assertFalse(supports_mode("kraken", "futures"))
        self.assertTrue(supports_mode("kraken", "margin_isolated"))

    def test_market_modes_enum_and_labels(self):
        self.assertIn("spot", MARKET_MODES)
        self.assertIn("futures", MARKET_MODES)

    def test_catalog_functions(self):
        only = exchange_catalog("binance")
        self.assertEqual(set(only), {"binance"})
        self.assertEqual(exchange_catalog("notanexchange"), {})


if __name__ == "__main__":
    unittest.main()