from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.cms_core import CMSEngine
from backend.cmsc_exchange import quote_cmsc
from backend.cmsc_payment import CMSCPaymentStore


def main() -> None:
    with NamedTemporaryFile(suffix='.db') as db:
        engine = CMSEngine(f'sqlite:///{db.name}')
        email = 'payment-test@example.com'
        engine.create_user(email, 'secret')
        engine.get_or_create_wallet(email)

        quote = quote_cmsc(10, 'EUR', 0.02)
        assert quote['cmsc_amount'] == 10.0
        assert quote['gross_payment'] == 10.0
        assert quote['fee_amount'] == 0.2
        assert quote['payable_amount'] == 10.2

        store = CMSCPaymentStore(engine)
        pending = store.create(email, quote, 'cmsc_test_intent')
        assert pending['status'] == 'pending_payment'

        confirmed = store.confirm('cmsc_test_intent', 'test-provider', 'provider-ref-1', 10.2, 'EUR')
        assert confirmed['status'] == 'confirmed'
        assert confirmed['provider_reference'] == 'provider-ref-1'
        wallet = engine.get_or_create_wallet(email)
        assert abs(wallet['credits'] - 10.0) < 1e-9

        repeated = store.confirm('cmsc_test_intent', 'test-provider', 'provider-ref-1', 10.2, 'EUR')
        assert repeated['status'] == 'confirmed'
        wallet_after = engine.get_or_create_wallet(email)
        assert abs(wallet_after['credits'] - 10.0) < 1e-9

        try:
            store.confirm('cmsc_test_intent', 'test-provider', 'provider-ref-2', 10.2, 'EUR')
        except ValueError:
            pass
        else:
            raise AssertionError('A confirmed intent must not accept a second provider reference.')

        print('CMSC payment confirmation smoke: PASS')


if __name__ == '__main__':
    main()
