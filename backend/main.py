from pathlib import Path
import hashlib
import hmac
import os
import secrets
import time
import yaml
import requests
from collections import Counter
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
import ccxt
from urllib.parse import urlencode

from .admin import router as admin_router
from .health import router as health_router
from .bot import HFTBot
from .cms_core import CMSEngine
from .hft_brain import CMSProductionHFTBot
from .modules.strategy_manager import StrategyManager
from .market_history import (
    ensure_table, load_candles, refresh_candles, load_history, refresh_history,
    load_news, refresh_news, analyze_news_sentiment,
)
from .strategy_performance import (
    LICENSE_DURATIONS_DAYS,
    evaluate_strategies,
    price_for_duration,
)
from .risk_management import RiskManager

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Daily Compound Harvester CMS", version="1.0.0")
if os.getenv("APP_ENV", "development").lower() == "production" and not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY must be configured in production.")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "development-only-change-me"),
    max_age=3600,
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")
app.include_router(admin_router)
app.include_router(health_router)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def template_url_for(name: str, **values):
    if name == "static" and "filename" in values:
        values["path"] = values.pop("filename")
    return app.url_path_for(name, **values)

templates.env.globals["url_for"] = template_url_for
engine = CMSEngine()
risk_manager = RiskManager()
bot = HFTBot()
production_bot = CMSProductionHFTBot()
strategy_manager = StrategyManager()
MARKET_DATABASE = str(BASE_DIR / "cms_v12.db")
SUPPORTED_MARKET_EXCHANGES = {"binance", "bybit", "kraken", "okx", "bitfinex"}
WALLET_PROVIDERS = ("MetaMask", "Trust Wallet", "Binance Wallet", "WalletConnect", "Ledger", "Trezor")
SOCIAL_PROVIDERS = {
    "google": {"client_id_env": "GOOGLE_CLIENT_ID", "client_secret_env": "GOOGLE_CLIENT_SECRET", "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth", "token_url": "https://oauth2.googleapis.com/token", "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo", "scope": "openid email profile"},
    "github": {"client_id_env": "GITHUB_CLIENT_ID", "client_secret_env": "GITHUB_CLIENT_SECRET", "authorize_url": "https://github.com/login/oauth/authorize", "token_url": "https://github.com/login/oauth/access_token", "userinfo_url": "https://api.github.com/user", "scope": "read:user user:email"},
}
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")
CMSC_PAYMENT_CURRENCIES = ("EUR", "USD", "GBP", "RUB", "CHF")
CRYPTO_PAYOUT_ASSETS = ("USDT", "USDC", "BTC")
CARD_PAYOUT_SERVICES = ("Stripe", "PayPal", "Adyen", "Revolut Business")
_payout_settings = {"crypto_asset": "USDT", "crypto_network": "", "crypto_address": "", "card_provider": "Stripe", "card_recipient": "", "card_currency": "EUR"}
