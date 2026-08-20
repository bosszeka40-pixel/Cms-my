from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import cmsc_exchange


def main():
    rates = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "RUB": 0.010, "CHF": 1.05, "USDT": 0.92, "USDC": 0.92, "BTC": 55000.0}
    original = cmsc_exchange.current_eur_rate
    cmsc_exchange.current_eur_rate = lambda currency: rates[currency]
    try:
        quote = cmsc_exchange.quote_cmsc(100, "USD", 0.02)
        assert quote["cmsc_eur_rate"] == 1.0
        assert quote["gross_payment"] == 108.6956521739
        assert round(quote["fee_amount"], 8) == 2.17391304
        assert round(quote["payable_amount"], 8) == 110.86956522
        crypto_quote = cmsc_exchange.quote_cmsc(10, "USDT", 0.01)
        assert crypto_quote["currency"] == "USDT"
        assert crypto_quote["payable_amount"] > crypto_quote["gross_payment"]
    finally:
        cmsc_exchange.current_eur_rate = original

    try:
        cmsc_exchange.quote_cmsc(10, "JPY", 0.02)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported currency must fail")

    print("CMSC exchange quote smoke OK")


if __name__ == "__main__":
    main()
