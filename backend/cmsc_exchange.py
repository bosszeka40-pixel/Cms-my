from __future__ import annotations

import secrets
from datetime import datetime, timezone

import ccxt
import requests

FIAT_CURRENCIES = ("EUR", "USD", "GBP", "RUB", "CHF")
CRYPTO_CURRENCIES = ("USDT", "USDC", "BTC")
PAYMENT_CURRENCIES = FIAT_CURRENCIES + CRYPTO_CURRENCIES
DEFAULT_FEE_RATE = 0.02


def _fiat_rate(currency: str) -> float:
    if currency == "EUR":
        return 1.0
    response = requests.get("https://api.frankfurter.app/latest", params={"from": "EUR", "to": currency}, timeout=8)
    response.raise_for_status()
    rate = float(response.json()["rates"][currency])
    if rate <= 0:
        raise ValueError("Получен некорректный курс фиатной валюты.")
    return rate


def _crypto_eur_rate(currency: str) -> float:
    exchange = ccxt.binance({"enableRateLimit": True, "timeout": 10000})
    btc_eur = float(exchange.fetch_ticker("BTC/EUR")["last"])
    if btc_eur <= 0:
        raise ValueError("Не удалось получить курс BTC/EUR.")
    if currency == "BTC":
        return btc_eur
    pair = f"BTC/{currency}"
    btc_crypto = float(exchange.fetch_ticker(pair)["last"])
    if btc_crypto <= 0:
        raise ValueError(f"Не удалось получить курс {currency}.")
    return btc_eur / btc_crypto


def current_eur_rate(currency: str) -> float:
    currency = currency.upper().strip()
    if currency not in PAYMENT_CURRENCIES:
        raise ValueError("Неподдерживаемая валюта оплаты.")
    if currency in FIAT_CURRENCIES:
        return _fiat_rate(currency)
    return _crypto_eur_rate(currency)


def quote_cmsc(amount_cmsc: float, currency: str, fee_rate: float = DEFAULT_FEE_RATE) -> dict:
    if amount_cmsc <= 0:
        raise ValueError("Количество CMSC должно быть положительным.")
    if fee_rate < 0 or fee_rate > 0.25:
        raise ValueError("Комиссия Exchange должна быть от 0% до 25%.")
    currency = currency.upper().strip()
    eur_per_payment_unit = current_eur_rate(currency)
    gross_payment = float(amount_cmsc) / eur_per_payment_unit
    fee = gross_payment * fee_rate
    payable = gross_payment + fee
    return {"cmsc_amount": round(float(amount_cmsc), 8), "cmsc_eur_rate": 1.0, "currency": currency, "eur_per_payment_unit": round(eur_per_payment_unit, 10), "gross_payment": round(gross_payment, 10), "fee_rate": round(fee_rate, 8), "fee_amount": round(fee, 10), "payable_amount": round(payable, 10), "quoted_at": datetime.now(timezone.utc).isoformat(), "status": "quote"}


def create_payment_intent(engine, email: str, amount_cmsc: float, currency: str, fee_rate: float) -> dict:
    quote = quote_cmsc(amount_cmsc, currency, fee_rate)
    intent_id = f"cmsc_{secrets.token_urlsafe(18)}"
    context = f"intent={intent_id}; cmsc={quote['cmsc_amount']:.8f}; currency={quote['currency']}; gross={quote['gross_payment']:.10f}; fee={quote['fee_amount']:.10f}; payable={quote['payable_amount']:.10f}; rate={quote['eur_per_payment_unit']:.10f}"
    engine.record_audit("cmsc_exchange_payment_intent", context, email)
    return {**quote, "intent_id": intent_id, "status": "pending_payment"}
