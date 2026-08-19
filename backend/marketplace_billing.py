from __future__ import annotations

from datetime import datetime, timedelta

from .cms_core import AuditLog, Plugin, User, UserPlugin, Wallet


LICENSE_DAYS = {1, 3, 7, 14, 15, 30}


def purchase_strategy_with_cmsc(
    engine,
    email: str,
    plugin_name: str,
    price_eur: float,
    duration_days: int,
) -> dict:
    """Purchase/renew a strategy using the internal CMSC balance.

    CMSC is the internal settlement unit and is fixed at 1 CMSC = 1 EUR.
    A paid purchase debits CMSC and creates/extends the user's plugin access
    in one database transaction. Free strategies never debit the wallet.
    """
    if duration_days not in LICENSE_DAYS:
        raise ValueError("Недопустимый срок доступа.")
    price = round(max(0.0, float(price_eur)), 8)
    session = engine.SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        plugin = session.query(Plugin).filter(Plugin.name == plugin_name).first()
        if not user or not plugin:
            return None

        wallet = session.query(Wallet).filter(Wallet.user_id == user.id).first()
        if price > 0:
            if not wallet or (wallet.credits or 0.0) + 1e-9 < price:
                raise ValueError("Недостаточно CMSC для покупки стратегии.")
            wallet.credits = round((wallet.credits or 0.0) - price, 8)

        now = datetime.utcnow()
        purchase = (
            session.query(UserPlugin)
            .filter_by(user_id=user.id, plugin_id=plugin.id)
            .first()
        )
        if not purchase:
            purchase = UserPlugin(
                user_id=user.id,
                plugin_id=plugin.id,
                active=False,
                purchased_at=now,
                access_until=now + timedelta(days=duration_days),
            )
            session.add(purchase)
        else:
            purchase.access_until = now + timedelta(days=duration_days)

        session.add(
            AuditLog(
                user_id=email,
                action="strategy_purchase",
                context=f"plugin={plugin.name}; cmsc={price:.8f}; days={duration_days}",
            )
        )
        session.commit()
        return {
            "name": plugin.name,
            "price_eur": price,
            "price_cmsc": price,
            "currency": "CMSC",
            "cmsc_rate_eur": 1.0,
            "active": purchase.active,
            "access_until": purchase.access_until.isoformat(),
            "access_days": duration_days,
            "balance_cmsc": round((wallet.credits if wallet else 0.0) or 0.0, 8),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
