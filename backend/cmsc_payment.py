from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from .cms_core import AuditLog, Base, User, Wallet


class CMSCPaymentIntent(Base):
    __tablename__ = 'cmsc_payment_intents'

    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    cmsc_amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    eur_per_payment_unit = Column(Float, nullable=False)
    gross_payment = Column(Float, nullable=False)
    fee_rate = Column(Float, nullable=False)
    fee_amount = Column(Float, nullable=False)
    payable_amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default='pending_payment', index=True)
    provider = Column(String, nullable=True)
    provider_reference = Column(String, unique=True, nullable=True, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CMSCPaymentStore:
    def __init__(self, engine):
        self.engine = engine
        Base.metadata.create_all(bind=engine.engine)

    def _session(self):
        return self.engine.SessionLocal()

    def create(self, email: str, quote: dict[str, Any], intent_id: str) -> dict[str, Any]:
        session = self._session()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                raise ValueError('Пользователь не найден.')
            existing = session.query(CMSCPaymentIntent).filter(CMSCPaymentIntent.intent_id == intent_id).first()
            if existing:
                return self._dict(existing)
            row = CMSCPaymentIntent(
                intent_id=intent_id,
                user_id=user.id,
                email=email,
                cmsc_amount=float(quote['cmsc_amount']),
                currency=str(quote['currency']).upper(),
                eur_per_payment_unit=float(quote['eur_per_payment_unit']),
                gross_payment=float(quote['gross_payment']),
                fee_rate=float(quote['fee_rate']),
                fee_amount=float(quote['fee_amount']),
                payable_amount=float(quote['payable_amount']),
                status='pending_payment',
            )
            session.add(row)
            session.add(AuditLog(user_id=email, action='cmsc_payment_intent_created', context=intent_id))
            session.commit()
            session.refresh(row)
            return self._dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def confirm(self, intent_id: str, provider: str, provider_reference: str, paid_amount: float, currency: str) -> dict[str, Any]:
        if paid_amount <= 0:
            raise ValueError('Сумма подтверждённого платежа должна быть положительной.')
        provider_reference = provider_reference.strip()
        if not provider_reference:
            raise ValueError('Не указан reference платежа провайдера.')
        session = self._session()
        try:
            row = session.query(CMSCPaymentIntent).filter(CMSCPaymentIntent.intent_id == intent_id).with_for_update().first()
            if not row:
                raise ValueError('Payment intent не найден.')
            if row.status == 'confirmed':
                return self._dict(row)
            if row.status != 'pending_payment':
                raise ValueError('Payment intent нельзя подтвердить из текущего статуса.')
            if row.provider_reference and row.provider_reference != provider_reference:
                raise ValueError('Payment intent уже связан с другим provider reference.')
            if row.currency.upper() != currency.upper():
                raise ValueError('Валюта подтверждённого платежа не совпадает с intent.')
            tolerance = max(0.00000001, row.payable_amount * 0.0001)
            if abs(float(paid_amount) - row.payable_amount) > tolerance:
                raise ValueError('Сумма подтверждённого платежа не совпадает с intent.')
            wallet = session.query(Wallet).filter(Wallet.user_id == row.user_id).first()
            if not wallet:
                wallet = Wallet(user_id=row.user_id, credits=0.0)
                session.add(wallet)
                session.flush()
            wallet.credits = float(wallet.credits or 0.0) + row.cmsc_amount
            row.status = 'confirmed'
            row.provider = provider.strip() or None
            row.provider_reference = provider_reference
            row.confirmed_at = datetime.utcnow()
            session.add(AuditLog(user_id=row.email, action='cmsc_payment_confirmed', context=f'intent={row.intent_id}; provider={row.provider}; reference={provider_reference}; cmsc={row.cmsc_amount:.8f}'))
            session.commit()
            session.refresh(row)
            return self._dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _dict(row: CMSCPaymentIntent) -> dict[str, Any]:
        return {
            'intent_id': row.intent_id,
            'email': row.email,
            'cmsc_amount': row.cmsc_amount,
            'currency': row.currency,
            'gross_payment': row.gross_payment,
            'fee_rate': row.fee_rate,
            'fee_amount': row.fee_amount,
            'payable_amount': row.payable_amount,
            'status': row.status,
            'provider': row.provider,
            'provider_reference': row.provider_reference,
            'confirmed_at': row.confirmed_at.isoformat() if row.confirmed_at else None,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }
