from pathlib import Path
from tempfile import TemporaryDirectory

from backend.cms_core import CMSEngine
from backend.marketplace_billing import purchase_strategy_with_cmsc

with TemporaryDirectory() as temp_dir:
    db_path = Path(temp_dir) / 'marketplace-test.db'
    engine = CMSEngine(f'sqlite:///{db_path}')
    email = 'billing-test@example.local'
    engine.create_user(email, 'test-password')
    engine.create_plugin('paid_test_strategy', 12.0, 'billing test')
    engine.add_wallet_credits(email, 20.0)

    purchase = purchase_strategy_with_cmsc(engine, email, 'paid_test_strategy', 12.0, 15)
    assert purchase['price_cmsc'] == 12.0
    assert purchase['cmsc_rate_eur'] == 1.0
    assert purchase['balance_cmsc'] == 8.0

    try:
        purchase_strategy_with_cmsc(engine, email, 'paid_test_strategy', 9.0, 15)
    except ValueError as exc:
        assert 'Недостаточно CMSC' in str(exc)
    else:
        raise AssertionError('Insufficient CMSC purchase was accepted')

    engine.create_plugin('free_test_strategy', 0.0, 'free billing test')
    free_purchase = purchase_strategy_with_cmsc(engine, email, 'free_test_strategy', 0.0, 15)
    assert free_purchase['price_cmsc'] == 0.0
    assert free_purchase['balance_cmsc'] == 8.0

print('CMSC marketplace billing OK')
