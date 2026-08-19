from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import backend.cmsc_exchange as exchange


def expect_value_error(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except ValueError:
        return
    raise AssertionError('Expected ValueError')


def main():
    original = exchange.current_eur_rate
    exchange.current_eur_rate = lambda currency: 1.0
    try:
        expect_value_error(exchange.quote_cmsc, 0, 'EUR')
        expect_value_error(exchange.quote_cmsc, -1, 'EUR')
        expect_value_error(exchange.quote_cmsc, 10, 'EUR', -0.01)
        expect_value_error(exchange.quote_cmsc, 10, 'EUR', 0.26)
        expect_value_error(exchange.quote_cmsc, 10, 'JPY')

        quote = exchange.quote_cmsc(100, ' eur ', 0.02)
        assert quote['currency'] == 'EUR'
        assert quote['gross_payment'] == 100.0
        assert quote['fee_amount'] == 2.0
        assert quote['payable_amount'] == 102.0
    finally:
        exchange.current_eur_rate = original

    print('CMSC exchange validation smoke OK')


if __name__ == '__main__':
    main()
