import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.main import cmsc_exchange_quote


def main():
    quote = cmsc_exchange_quote("100", "USD")
    assert quote["cmsc"] == 100
    assert quote["currency"] == "USD"
    assert quote["eur_value"] == 100.0
    assert quote["rate"] > 0
    assert quote["commission_rate"] >= 0
    assert quote["payable"] > 0
    assert quote["source"]

    eur = cmsc_exchange_quote("10", "EUR")
    assert eur["payable"] >= 10
    assert eur["rate"] == 1.0

    print("CMSC exchange quote path OK")


if __name__ == "__main__":
    main()
