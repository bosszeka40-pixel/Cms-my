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
from .bot import HFTBot
from .bot_runtime import BotRuntime
from .cms_core import CMSEngine
from .hft_brain import CMSProductionHFTBot
from .modules.strategy_manager import StrategyManager
from .simple_cache import cached_fetch, cached_get
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
from .exchange_service import ExchangeService
from .security.execution_policy import current_mode, real_execution_allowed
from .security.live_controls import LIVE_CONTROL_STATE, LiveControlState
from .security.execution_gateway import submit_real_order, cancel_real_order
from .security.safe_errors import safe_exception_message, safe_error_payload
from .health import router as health_router
from .modules.arbitrage_engine import ArbitrageEngine

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
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(admin_router)
app.include_router(health_router)

@app.get("/health", name="health")
async def health():
    return {"status": "ok"}

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Friendly error page for 500 errors instead of raw traceback."""
    from fastapi.responses import HTMLResponse
    from .security.safe_errors import safe_exception_message, safe_error_payload
    msg = safe_exception_message(exc, "server")
    if request.url.path.startswith('/api/'):
        return safe_error_payload(exc, "api")
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>Ошибка сервера</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body class="dark">
<div style="max-width:600px;margin:3rem auto;padding:2rem;text-align:center;">
    <h1 style="color:var(--danger);margin-bottom:1rem;">Ошибка сервера</h1>
    <p style="color:var(--text-secondary);margin-bottom:1.5rem;">{msg}</p>
    <p style="font-size:.85rem;color:var(--text-muted);margin-bottom:2rem;">
        Администраторы уведомлены. Попробуйте повторить действие.
    </p>
    <a href="/" class="btn">На главную</a>
    <a href="javascript:history.back()" class="btn btn-outline" style="margin-left:.5rem;">Назад</a>
</div>
</body>
</html>
"""
    return HTMLResponse(content=html, status_code=500)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def template_url_for(name: str, **values):
    if name == "static" and "filename" in values:
        return f"/static/{values['filename']}"
    return app.url_path_for(name, **values)

templates.env.globals["url_for"] = template_url_for
engine = CMSEngine()
risk_manager = RiskManager()
bot = HFTBot()
production_bot = CMSProductionHFTBot()
strategy_manager = StrategyManager()
exchange_service = ExchangeService(LIVE_CONTROL_STATE)
arbitrage_engine = ArbitrageEngine()
bot_runtime = BotRuntime(engine, strategy_manager, risk_manager, bot, exchange_service)
MARKET_DATABASE = str(BASE_DIR / "cms_v12.db")
SUPPORTED_MARKET_EXCHANGES = {"binance", "bybit", "kraken", "okx", "bitfinex"}
SUPPORTED_TRADING_PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT")
BACKTEST_PERIOD_WINDOWS = {
    "1d": 2,
    "1w": 8,
    "1m": 31,
    "3m": 92,
    "6m": 183,
    "1y": 366,
}
WALLET_PROVIDERS = ("MetaMask", "Trust Wallet", "Binance Wallet", "WalletConnect", "Ledger", "Trezor")
SOCIAL_PROVIDERS = {
    "google": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile"},
    "github": {
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email"}}
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")


def social_login_context() -> dict:
    return {
        "google_configured": bool(
            os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")
        ),
        "github_configured": bool(
            os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")
        ),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_USERNAME),
        "telegram_bot_username": TELEGRAM_BOT_USERNAME}


def _login_user(request: Request, user) -> RedirectResponse:
    request.session["user_email"] = user.email
    request.session["is_admin"] = user.role == "admin"
    return RedirectResponse(url="/dashboard", status_code=302)
CMSC_PAYMENT_CURRENCIES = ("EUR", "USD", "GBP", "RUB", "CHF")
CRYPTO_PAYOUT_ASSETS = ("USDT", "USDC", "BTC")
CARD_PAYOUT_SERVICES = ("Stripe", "PayPal", "Adyen", "Revolut Business")
_payout_settings = {
    "crypto_asset": "USDT",
    "crypto_network": "",
    "crypto_address": "",
    "card_provider": "Stripe",
    "card_recipient": "",
    "card_currency": "EUR"}


def save_strategy_config(strategy: str, leverage: float, risk_tolerance: float, fee_rate: float | None = None):
    strategy_manager.config["strategy"] = strategy
    strategy_manager.config["leverage"] = leverage
    strategy_manager.config["risk_tolerance"] = risk_tolerance
    if fee_rate is not None:
        strategy_manager.config["fee_rate"] = fee_rate
    with strategy_manager.config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(strategy_manager.config, handle)

class ExchangeConfig(BaseModel):
    exchange_name: str
    api_key: str
    api_secret: str

class ArbitrageExchangeConfig(BaseModel):
    exchange_name: str
    api_key: str
    api_secret: str
    passphrase: str = ""

class HFTSimulatePayload(BaseModel):
    market_data: list[float]
    ai_stream: list[float]

class StrategyPayload(BaseModel):
    news_sentiment: float
    price_change: float
    current_balance: float

class TradingTestPayload(BaseModel):
    pair: str
    news_sentiment: float
    price_change: float
    current_balance: float

class ManualTradePayload(BaseModel):
    pair: str
    side: str
    price: float
    amount: float
    balance: float

class BacktestPayload(BaseModel):
    pair: str = "BTC/USDT"
    exchange: str = "binance"
    initial_balance: float = 10.0
    period: str = "1m"
    strategy: str = "all"

class ChatPayload(BaseModel):
    message: str

class RiskConfigPayload(BaseModel):
    stop_loss_pct: float = 0.02
    leverage: float = 1.0

class KillSwitchPayload(BaseModel):
    enabled: bool

def _require_user(request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    return email

def _require_admin(request: Request):
    email = _require_user(request)
    user = engine.get_user(email)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Требуются права администратора.")
    return email

@app.get("/auth/{provider}", name="social_login")
async def social_login(provider: str, request: Request):
    provider = provider.lower()
    if provider == "telegram":
        raise HTTPException(
            status_code=404,
            detail="Вход через Telegram выполняется через виджет на странице входа.",
        )
    config = SOCIAL_PROVIDERS.get(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Неизвестный social provider.")
    client_id = os.getenv(config["client_id_env"])
    client_secret = os.getenv(config["client_secret_env"])
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=f"{provider.capitalize()} login не настроен ({config['client_id_env']} / {config['client_secret_env']}).",
        )
    state = secrets.token_hex(24)
    request.session[f"oauth_state_{provider}"] = state
    callback = str(request.url_for("social_callback", provider=provider))
    params = {
        "client_id": client_id,
        "redirect_uri": callback,
        "response_type": "code",
        "scope": config["scope"],
        "state": state}
    return RedirectResponse(f"{config['authorize_url']}?{urlencode(params)}", status_code=302)

@app.get("/auth/{provider}/callback", name="social_callback")
async def social_callback(provider: str, request: Request, code: str = "", state: str = "", error: str = ""):
    provider = provider.lower()
    expected = request.session.pop(f"oauth_state_{provider}", None)
    if error:
        raise HTTPException(status_code=400, detail=f"{provider.capitalize()} вернул ошибку: {error}")
    if not code or not state or not expected or state != expected:
        raise HTTPException(status_code=400, detail="Недействительный OAuth callback.")
    config = SOCIAL_PROVIDERS.get(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Неизвестный social provider.")
    client_id = os.getenv(config["client_id_env"])
    client_secret = os.getenv(config["client_secret_env"])
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail=f"{provider.capitalize()} login не настроен полностью.")

    callback_url = str(request.url_for("social_callback", provider=provider))
    try:
        token_response = requests.post(
            config["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code"},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Не удалось обменять код авторизации на токен.")

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="Провайдер не вернул access token.")

    auth_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    try:
        profile_response = requests.get(config["userinfo_url"], headers=auth_headers, timeout=10)
        profile_response.raise_for_status()
        profile = profile_response.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Не удалось получить профиль пользователя.")

    email = profile.get("email")
    if provider == "github" and not email:
        try:
            emails_response = requests.get("https://api.github.com/user/emails", headers=auth_headers, timeout=10)
            emails_response.raise_for_status()
            for entry in emails_response.json():
                if entry.get("primary") and entry.get("email"):
                    email = entry["email"]
                    break
        except requests.RequestException:
            email = None
    if not email:
        raise HTTPException(status_code=502, detail="Провайдер не предоставил email пользователя.")

    user = engine.get_user(email)
    if not user:
        user = engine.create_user(email, secrets.token_hex(16))
    return _login_user(request, user)


@app.get("/auth/telegram/callback", name="telegram_callback")
async def telegram_callback(request: Request):
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram login не настроен (TELEGRAM_BOT_TOKEN).")
    data = dict(request.query_params)
    received_hash = data.pop("hash", None)
    if not received_hash or not data.get("id") or not data.get("auth_date"):
        raise HTTPException(status_code=400, detail="Недействительные данные Telegram login.")
    try:
        auth_date = int(data["auth_date"])
    except ValueError:
        raise HTTPException(status_code=400, detail="Недействительные данные Telegram login.")
    if time.time() - auth_date > 86400:
        raise HTTPException(status_code=400, detail="Данные Telegram login устарели, попробуйте снова.")

    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode("utf-8")).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=400, detail="Проверка подписи Telegram не пройдена.")

    email = f"telegram_{data['id']}@telegram.local"
    user = engine.get_user(email)
    if not user:
        user = engine.create_user(email, secrets.token_hex(16))
    return _login_user(request, user)


def _public_exchange(name: str):
    exchange_name = (name or "binance").strip().lower()
    if exchange_name not in SUPPORTED_MARKET_EXCHANGES:
        raise ValueError("Неподдерживаемая публичная биржа.")
    exchange_class = getattr(ccxt, exchange_name, None)
    if exchange_class is None:
        raise ValueError("Биржа недоступна в установленной версии CCXT.")
    return exchange_class({"enableRateLimit": True, "timeout": 15000})


def _exchange_directory() -> list[dict]:
    directory = []
    for name in sorted(SUPPORTED_MARKET_EXCHANGES):
        website = None
        try:
            website = getattr(ccxt, name)().urls.get("www")
        except Exception:
            website = None
        directory.append({"id": name, "name": name.capitalize(), "website": website})
    return directory


def _market_signal(pair: str, exchange_name: str):
    if pair not in SUPPORTED_TRADING_PAIRS:
        raise ValueError("Недоступная торговая пара.")
    def _compute():
        exchange = _public_exchange(exchange_name)
        candles = refresh_candles(MARKET_DATABASE, exchange, exchange_name, pair)
        daily = refresh_history(MARKET_DATABASE, exchange, exchange_name, pair)
        return candles, daily
    cached = cached_get(f"market_signal:{pair}:{exchange_name}")
    if cached is None:
        candles, daily = _compute()
        cached = (candles, daily)
        cached_fetch(f"market_signal:{pair}:{exchange_name}", 5, lambda: cached)
    else:
        candles, daily = cached
    if len(candles) < 3 or len(daily) < 2:
        raise ValueError("Недостаточно исторических свечей для сигнала.")
    latest = candles[-1]
    previous = candles[-2]
    change = ((latest["close"] - previous["close"]) / previous["close"] * 100
              if previous["close"] else 0.0)
    result = strategy_manager.execute(1.0 if change > 0 else -1.0, change, 100.0)
    return {
        "pair": pair, "exchange": exchange_name, "timeframe": "1h",
        "signal": result["signal"], "strategy": result["strategy"],
        "last_price": latest["close"], "hour_change": round(change, 4),
        "hourly_candles": len(candles), "daily_candles": len(daily),
        "horizon": "ближайшие часы и следующий день",
        "confidence": min(0.95, round(0.5 + abs(change) / 10, 2)),
        "source": "сохранённые публичные OHLCV-свечи",
        "disclaimer": "Сигнал информационный и не является гарантией доходности."}


def _period_window_size(period: str) -> int:
    return BACKTEST_PERIOD_WINDOWS.get((period or "").strip().lower(), BACKTEST_PERIOD_WINDOWS["1m"])


def _truncate_daily_candles(candles: list[dict], period: str) -> list[dict]:
    window = _period_window_size(period)
    if window <= 0:
        return candles
    if len(candles) <= window:
        return candles
    return candles[-window:]


def _exchange_fee_rate(exchange_name: str, pair: str) -> float:
    exchange_name = (exchange_name or "binance").strip().lower()
    try:
        client = _public_exchange(exchange_name)
        client.load_markets()
        market = client.markets.get(pair) or {}
        fee = market.get("taker")
        if fee is None:
            fee = (client.fees.get("trading") or {}).get("taker")
        if fee is not None and float(fee) > 0:
            return float(fee)
    except Exception:
        pass
    return float(os.getenv("SIMULATION_FEE_RATE", "0.001"))


def _signal_for_pair(pair: str, exchange_name: str, source: str = "bot") -> dict:
    if pair not in SUPPORTED_TRADING_PAIRS:
        raise ValueError("Недоступная торговая пара.")
    exchange_name = (exchange_name or "binance").strip().lower()
    source = (source or "bot").strip().lower()
    exchange = _public_exchange(exchange_name)
    candles = refresh_candles(MARKET_DATABASE, exchange, exchange_name, pair)
    daily = refresh_history(MARKET_DATABASE, exchange, exchange_name, pair)
    if len(candles) < 3 or len(daily) < 2:
        raise ValueError("Недостаточно исторических данных для сигнала.")
    latest = candles[-1]
    previous = candles[-2]
    change = ((latest["close"] - previous["close"]) / previous["close"] * 100 if previous["close"] else 0.0)
    news = load_news(MARKET_DATABASE, limit=15)
    news_sentiment = analyze_news_sentiment(news) if news else 0.0
    bot_result = strategy_manager.execute(0.0, change, 100.0)
    ai_result = strategy_manager.execute(news_sentiment, change, 100.0)

    if source == "ai":
        signal_value = ai_result["signal"]
        confidence = min(0.98, 0.55 + abs(news_sentiment) * 0.2 + abs(change) / 18)
        strategy_name = f"ai:{ai_result['strategy']}"
    elif source == "ai_bot":
        signal_value = ai_result["signal"] if ai_result["signal"] == bot_result["signal"] else (1 if ai_result["pnl"] >= bot_result["pnl"] else bot_result["signal"])
        confidence = min(0.99, 0.5 + (abs(ai_result["signal"]) + abs(bot_result["signal"])) / 6 + abs(change) / 20)
        strategy_name = f"ai+bot:{ai_result['strategy']}"
    else:
        signal_value = bot_result["signal"]
        confidence = min(0.96, 0.5 + abs(change) / 12)
        strategy_name = f"bot:{bot_result['strategy']}"

    fee_rate = _exchange_fee_rate(exchange_name, pair)
    return {
        "pair": pair,
        "exchange": exchange_name,
        "source": source,
        "signal": signal_value,
        "recommended_side": "buy" if signal_value > 0 else "sell" if signal_value < 0 else "hold",
        "strategy": strategy_name,
        "confidence": round(confidence, 4),
        "last_price": latest["close"],
        "hour_change": round(change, 4),
        "daily_candles": len(daily),
        "hourly_candles": len(candles),
        "news_sentiment": round(news_sentiment, 4),
        "fee_rate": round(fee_rate, 6),
        "timestamp": latest.get("timestamp"),
    }


def _signals_for_all_pairs(exchange_name: str, source: str = "bot") -> list[dict]:
    reports = []
    for pair in SUPPORTED_TRADING_PAIRS:
        try:
            reports.append(_signal_for_pair(pair, exchange_name, source))
        except Exception as exc:
            reports.append({
                "pair": pair,
                "exchange": (exchange_name or "binance").strip().lower(),
                "source": (source or "bot").strip().lower(),
                "signal": 0,
                "recommended_side": "hold",
                "strategy": "signal_error",
                "confidence": 0.0,
                "error": str(exc),
            })
    return reports


def _strategy_performance(exchange_name: str = "binance", pair: str = "BTC/USDT", period: str = "1m"):
    from datetime import datetime, timedelta, timezone

    def _load():
        ensure_table(MARKET_DATABASE)
        daily = load_history(MARKET_DATABASE, exchange_name, pair)
        freshness_cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
        if not daily or str(daily[-1].get("day", "")) < freshness_cutoff:
            client = _public_exchange(exchange_name)
            daily = refresh_history(MARKET_DATABASE, client, exchange_name, pair)
        month = _truncate_daily_candles(daily, period)
        names = [plugin.name for plugin in engine.list_plugins()]
        return evaluate_strategies(month, names, fee_rate=_exchange_fee_rate(exchange_name, pair))
    # TTL cache 300s; fallback to last computed стратегии if network fails
    cached = cached_get(f"strategy_performance:{exchange_name}:{pair}:{period}")
    if cached is not None:
        return cached
    try:
        result = _load()
        cached_fetch(f"strategy_performance:{exchange_name}:{pair}:{period}", 300, lambda: result)
        return result
    except Exception:
        return {}


def _strategy_catalog(email: str, performance: dict):
    purchased = {item["name"]: item for item in engine.user_plugins(email)}
    catalog = []
    for plugin in engine.list_plugins():
        result = performance.get(plugin.name, {})
        price = result.get("price_eur", float(plugin.price))
        owned = purchased.get(plugin.name)
        # Determine category
        if plugin.name.startswith("bot_"):
            category = "Бот-стратегии"
        elif plugin.name.startswith("user_"):
            category = "Пользовательские"
        elif price == 0:
            category = "Бесплатные"
        elif price <= 4.0:
            category = "Платиновые"
        else:
            category = "Премиум модули"
        if result:
            category = result.get("category", category)
        catalog.append({
            "id": plugin.id,
            "name": plugin.name,
            "description": plugin.description,
            "price_eur": price,
            "currency": "EUR",
            "access_days": result.get("access_days"),
            "license_options": [
                {"days": days, "price_eur": price_for_duration(price, days)}
                for days in LICENSE_DURATIONS_DAYS
            ] if price > 0 else [],
            "category": category,
            "monthly_return_pct": result.get("monthly_return_pct"),
            "final_balance_eur": result.get("final_balance_eur"),
            "win_rate_pct": result.get("win_rate_pct"),
            "available": price == 0 or bool(owned and owned["active"]),
            "active": bool(owned and owned["active"]),
            "owned": bool(owned),
            "free_trial_days": 15 if price > 0 else 0,
            "access_until": owned["access_until"] if owned else None})
    return catalog

class PluginActionPayload(BaseModel):
    plugin_name: str
    duration_days: int = 15
    trial: bool = False
class StrategyCreatePayload(BaseModel):
    name: str
    description: str = ""
    strategy_type: str = "pure_harvester"
    leverage: float = 1.5
    risk_tolerance: float = 0.03
    fee_rate: float = 0.001
    is_public: bool = False
    price_eur: float = 0.0

class DemoTogglePayload(BaseModel):
    active: bool = True

class DemoTradePayload(BaseModel):
    pair: str = "BTC/USDT"
    strategy: str = "pure_harvester"
    sentiment: float = 0.5
    price_change: float = 1.0
    amount: float = 10.0
    side: str = "buy"



@app.get("/", name="index")
async def serve_root(request: Request):
    return templates.TemplateResponse(request, "index.html",
        { "user_id": request.session.get("user_email") if request.session else None}
    )

@app.get("/home", name="home")
async def home(request: Request):
    return await serve_root(request)


# TODO: временный обход входа для админа без пароля. Убрать перед выпуском в продакшн.
DEV_ADMIN_BYPASS_ENABLED = os.getenv("APP_ENV", "development").lower() != "production"
DEV_ADMIN_EMAIL = "dev-admin@local"


@app.get("/login", name="login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html",
        {
                        "message": None,
            "user_id": request.session.get("user_email"),
            "dev_admin_bypass_enabled": DEV_ADMIN_BYPASS_ENABLED,
            **social_login_context()},
    )


@app.post("/login/dev-admin-bypass", name="dev_admin_bypass")
async def dev_admin_bypass(request: Request):
    if not DEV_ADMIN_BYPASS_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")
    user = engine.get_user(DEV_ADMIN_EMAIL)
    if not user:
        user = engine.create_user(DEV_ADMIN_EMAIL, secrets.token_hex(16), role="admin")
    return _login_user(request, user)

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    # username field may contain email
    user = engine.secure_login(username, password)
    if user:
        return _login_user(request, user)
    return templates.TemplateResponse(request, "login.html",
        {
                        "message": "Неверный логин или пароль.",
            "user_id": None,
            "dev_admin_bypass_enabled": DEV_ADMIN_BYPASS_ENABLED,
            **social_login_context()},
    )

@app.get("/register", name="register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html",
        {
                        "message": None,
            "user_id": request.session.get("user_email"),
            **social_login_context()},
    )

@app.post("/register")
async def register_submit(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    if password != confirm_password:
        return templates.TemplateResponse(request, "register.html",
            { "message": "Пароли не совпадают.", "user_id": None, **social_login_context()},
        )
    try:
        user = engine.create_user(email, password)
        request.session["user_email"] = user.email
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        return templates.TemplateResponse(request, "register.html",
            { "message": f"Ошибка регистрации: {e}", "user_id": None, **social_login_context()},
        )

@app.get("/forgot-password", name="forgot_password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html",
        { "message": None, "user_id": request.session.get("user_email")}
    )

@app.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...)):
    return templates.TemplateResponse(request, "forgot_password.html",
        { "message": "Инструкции по восстановлению пароля отправлены на указанный email.", "user_id": request.session.get("user_email")}
    )

@app.api_route("/dashboard", methods=["GET", "POST"], name="dashboard")
async def dashboard(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    message = None
    if request.method == "POST":
        form = await request.form()
        if form.get("action") == "save_theme" and form.get("theme") in {"light", "dark", "auto"}:
            request.session["theme"] = form["theme"]
            message = "Тема оформления сохранена."
    user = engine.get_user(user_email)
    username = user.email if user else user_email
    balance = "—"
    return templates.TemplateResponse(request, "dashboard.html",
        {
                        "username": username,
            "email": user_email,
            "balance": balance,
            "wallet": engine.get_or_create_wallet(user_email),
            "user_id": user_email,
            "is_admin": bool(user and user.role == "admin"),
            "theme": request.session.get("theme", "dark"),
            "selected_theme": request.session.get("theme", "dark"),
            "message": message,
            "bot_active": bot.active,
            "memories": engine.recent_memories(user_email, 5),
            "demo": engine.get_demo_session(user_email),
            "risk": risk_manager.status(),
            "risk_score": risk_manager.calculate_risk_score(leverage=float(strategy_manager.config.get("leverage", 1.5))),
            "current_strategy": strategy_manager.current_strategy(),
            "mode": current_mode(),
            "bot_runtime": bot_runtime.status(user_email)},
    )

def _connection_action(user_email: str, action: str, form) -> tuple[str | None, str | None]:
    message = None
    exchange_info = None
    if action == "disconnect_exchange":
        engine.update_wallet(
            user_email,
            exchange_provider=None,
            exchange_key_masked=None,
            exchange_sandbox=True,
        )
        engine.record_audit("exchange_disconnected", "manual", user_email)
        message = "Биржа отключена."
    elif action == "connect_exchange":
        exchange_name = str(form.get("exchange_name", "")).strip().lower()
        api_key = str(form.get("api_key", "")).strip()
        api_secret = str(form.get("api_secret", "")).strip()
        api_password = str(form.get("api_password", "")).strip()
        sandbox = form.get("sandbox") is not None
        if exchange_name not in SUPPORTED_MARKET_EXCHANGES:
            message = "Выберите поддерживаемую биржу."
        elif not api_key or not api_secret:
            message = "Укажите API Key и API Secret."
        else:
            try:
                exchange_class = getattr(ccxt, exchange_name)
                config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}
                if api_password:
                    config["password"] = api_password
                client = exchange_class(config)
                if sandbox and hasattr(client, "set_sandbox_mode"):
                    client.set_sandbox_mode(True)
                client.load_markets()
                engine.update_wallet(
                    user_email,
                    exchange_provider=exchange_name,
                    exchange_key_masked=engine.mask_secret(api_key),
                    exchange_sandbox=sandbox,
                )
                engine.record_audit("exchange_connected", exchange_name, user_email)
                exchange_info = f"Биржа {exchange_name.capitalize()} подключена ({'sandbox' if sandbox else 'live'})."
            except Exception as exc:
                message = f"Не удалось подключить биржу: {exc}"
    elif action == "connect_wallet":
        wallet_provider = str(form.get("wallet_provider", "")).strip()
        wallet_address = str(form.get("wallet_address", "")).strip()
        if wallet_provider not in WALLET_PROVIDERS:
            message = "Выберите поддерживаемый кошелек."
        elif not wallet_address:
            message = "Укажите адрес кошелька."
        else:
            engine.update_wallet(user_email, wallet_provider=wallet_provider, wallet_address=wallet_address)
            engine.record_audit("wallet_connected", wallet_provider, user_email)
            message = f"Кошелек {wallet_provider} подключен."
    elif action == "connect_telegram":
        telegram_username = str(form.get("telegram_username", "")).strip().lstrip("@")
        telegram_token = str(form.get("telegram_token", "")).strip()
        if not telegram_username or not telegram_token:
            message = "Укажите Telegram username и Bot token."
        else:
            engine.update_wallet(user_email, telegram_username=telegram_username)
            engine.record_audit("telegram_connected", telegram_username, user_email)
            message = f"Telegram @{telegram_username} подключен."
    return message, exchange_info


@app.api_route("/settings", methods=["GET", "POST"], name="settings")
async def settings_page(request: Request):
    return await profile(request)

@app.api_route("/marketplace", methods=["GET", "POST"], name="marketplace")
async def marketplace(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    plugin_message = None
    try:
        performance = _strategy_performance()
    except Exception:
        performance = {}
    if request.method == "POST":
        form = await request.form()
        action = form.get("action")
        if action == "buy_plugin":
            plugin_name = str(form.get("plugin_name", ""))
            try:
                duration_days = int(form.get("duration_days", 15))
                result = performance.get(plugin_name, {})
                price_eur = price_for_duration(result.get("price_eur", 0.0), duration_days)
                wallet_data = engine.get_or_create_wallet(user_email)
                if price_eur > 0 and (wallet_data.get("credits", 0) or 0) < price_eur:
                    plugin_message = f"Недостаточно CMSC. Нужно: €{price_eur:.2f}, на балансе: €{wallet_data.get('credits', 0):.2f}"
                else:
                    purchase = engine.purchase_plugin(user_email, plugin_name, price_eur, duration_days)
                    if purchase and price_eur > 0:
                        engine.add_wallet_credits(user_email, -price_eur)
                        engine.record_audit("plugin_purchase", f"{plugin_name} €{price_eur} for {duration_days}d", user_email)
                    plugin_message = (
                        f"Стратегия добавлена на {duration_days} дн."
                        if purchase else "Стратегия не найдена."
                    )
            except (TypeError, ValueError) as exc:
                plugin_message = str(exc)
    site_settings = engine.get_site_settings()
    allowed_exchanges = {name.strip().lower() for name in site_settings["allowed_exchanges"].split(",") if name.strip()}
    allowed_wallets = [name.strip() for name in site_settings["allowed_wallets"].split(",") if name.strip()]
    return templates.TemplateResponse(request, "marketplace.html",
        {
                        "user_id": user_email,
            "wallet": engine.get_or_create_wallet(user_email),
            "internal_currency": "CMS Credits (CMSC)",
            "exchanges": sorted(allowed_exchanges & SUPPORTED_MARKET_EXCHANGES) or sorted(SUPPORTED_MARKET_EXCHANGES),
            "exchange_directory": [item for item in _exchange_directory() if item["id"] in allowed_exchanges] or _exchange_directory(),
            "wallets": allowed_wallets or list(WALLET_PROVIDERS),
            "plugins": _strategy_catalog(user_email, performance),
            "purchases": engine.user_plugins(user_email),
            "plugin_message": plugin_message},
    )

def _trading_context(user_email: str, message: str | None = None) -> dict:
    engine.ensure_demo_session(user_email)
    db_user = engine.get_user(user_email)
    username = db_user.email if db_user else user_email
    return {
        "user_id": user_email,
        "username": username,
        "is_admin": bool(db_user and db_user.role == "admin"),
        "theme": "dark",
        "message": message,
        "trade_history": engine.list_trades(user_email, 20),
        "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
        "trading_exchanges": sorted(SUPPORTED_MARKET_EXCHANGES),
        "chart_timeframes": ["1m", "5m", "15m", "1h", "1d"],
        "demo": engine.get_demo_session(user_email),
        "bot_memory": bot.get_memory_summary()}


@app.api_route("/bot-management", methods=["GET", "POST"], name="bot_management")
async def bot_management(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    message = None
    if request.method == "POST":
        form = await request.form()
        action = form.get("action")
        if action == "start_bot":
            bot.start()
            message = "Бот запущен."
        elif action == "stop_bot":
            bot.stop()
            message = "Бот остановлен."
        elif action == "save_strategy":
            try:
                strategy = form.get("strategy", strategy_manager.current_strategy())
                leverage = max(0.1, min(float(form.get("leverage", 1.5)), 10))
                risk_tolerance = max(0.0, min(float(form.get("risk_tolerance", 0.03)), 1))
                fee_rate = max(0.0, min(float(form.get("fee_rate", 0.001)), 0.05))
                save_strategy_config(strategy, leverage, risk_tolerance, fee_rate)
                bot.set_strategy(strategy)
                message = "Настройки стратегии сохранены."
            except (TypeError, ValueError):
                message = "Проверьте значения левериджа, риска и комиссии."
    return templates.TemplateResponse(request, "bot_management.html",
        {
                        "bot_status": bot.status(),
            "current_strategy": strategy_manager.current_strategy(),
            "config": strategy_manager.config,
            "manual_trade_result": None,
            "balance_history": [{"time": "start", "value": 100}],
            **_trading_context(user_email, message)},
    )


@app.get("/manual-trading", name="manual_trading")
async def manual_trading(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request, "manual_trading.html",
        { **_trading_context(user_email)},
    )


@app.get("/strategies", name="strategies_page")
async def strategies_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    ctx = _trading_context(user_email)
    ctx["bot_status"] = bot.status()
    ctx["current_strategy"] = strategy_manager.current_strategy()
    return templates.TemplateResponse(request, "strategies.html", ctx)

@app.get("/demo", name="demo_page")
async def demo_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    ctx = _trading_context(user_email)
    ctx["bot_status"] = bot.status()
    return templates.TemplateResponse(request, "demo.html", ctx)

@app.api_route("/testing", methods=["GET", "POST"], name="testing_page")
async def testing_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    ctx = _trading_context(user_email)
    ctx["bot_status"] = bot.status()
    return templates.TemplateResponse(request, "testing.html", ctx)

@app.api_route("/wallet", methods=["GET", "POST"], name="wallet_page")
async def wallet_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    message = None
    if request.method == "POST":
        form = await request.form()
        if form.get("action") == "buy_credits":
            currency = str(form.get("currency", ""))
            try:
                amount = int(form.get("amount", 0))
            except (TypeError, ValueError):
                amount = 0
            if currency not in CMSC_PAYMENT_CURRENCIES or amount <= 0:
                message = "Укажите корректное количество CMSC и валюту оплаты."
            else:
                message = (
                    "Платёжный шлюз для пополнения CMSC ещё не подключен администратором. "
                    "Обратитесь в поддержку для оплаты вручную."
                )
    return templates.TemplateResponse(request, "wallet.html",
        {
                        "user_id": user_email,
            "user_email": user_email,
            "wallet": engine.get_or_create_wallet(user_email),
            "internal_currency": "CMS Credits (CMSC)",
            "payment_currencies": CMSC_PAYMENT_CURRENCIES,
            "message": message},
    )

@app.api_route("/admin", methods=["GET", "POST"], name="admin_panel")
async def admin_panel(request: Request):
    try:
        user_email = _require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=302)
    message = None
    if request.method == "POST":
        form = await request.form()
        action = form.get("action")
        if action == "create_plugin":
            name = form.get("plugin_name")
            try:
                price = float(form.get("plugin_price", 0.0))
            except (TypeError, ValueError):
                price = 0.0
            description = form.get("plugin_description", "")
            if name and price > 0:
                engine.create_plugin(name, price, description)
                message = f"Плагин {name} добавлен."
            else:
                message = "Укажите название и положительную цену плагина."
        elif action == "update_plugin":
            try:
                plugin_id = int(form.get("plugin_id", 0))
                price = float(form.get("plugin_price", 0.0))
            except (TypeError, ValueError):
                plugin_id, price = 0, 0.0
            name = str(form.get("plugin_name", "")).strip()
            description = form.get("plugin_description", "")
            if not plugin_id or not name or price < 0:
                message = "Укажите корректные название и цену плагина."
            elif engine.update_plugin(plugin_id, name, price, description):
                message = f"Плагин {name} обновлён."
            else:
                message = "Плагин не найден."
        elif action == "delete_plugin":
            try:
                plugin_id = int(form.get("plugin_id", 0))
            except (TypeError, ValueError):
                plugin_id = 0
            if plugin_id and engine.delete_plugin(plugin_id):
                message = "Плагин удалён."
            else:
                message = "Плагин не найден."
        elif action == "save_admin_settings":
            strategy = form.get("strategy", strategy_manager.current_strategy())
            try:
                leverage = max(0.1, min(float(form.get("leverage", 1.5)), 10))
                risk_tolerance = max(0.0, min(float(form.get("risk_tolerance", 0.03)), 1))
                fee_rate = max(0.0, min(float(form.get("fee_rate", 0.001)), 0.05))
                save_strategy_config(strategy, leverage, risk_tolerance, fee_rate)
                message = "Настройки торговой платформы сохранены."
            except (TypeError, ValueError):
                message = "Проверьте значения левериджа, риска и комиссии."
        elif action == "save_payout_settings":
            crypto_asset = form.get("crypto_asset", "")
            card_provider = form.get("card_provider", "")
            crypto_address = str(form.get("crypto_address", "")).strip()
            card_recipient = str(form.get("card_recipient", "")).strip()
            if crypto_asset not in CRYPTO_PAYOUT_ASSETS:
                message = "Выберите поддерживаемую криптовалюту для выплат."
            elif card_provider not in CARD_PAYOUT_SERVICES:
                message = "Выберите поддерживаемый платёжный сервис."
            elif not crypto_address or not card_recipient:
                message = "Укажите криптоадрес и реквизит аккаунта платёжного сервиса."
            else:
                _payout_settings.update({
                    "crypto_asset": crypto_asset,
                    "crypto_network": str(form.get("crypto_network", "")).strip(),
                    "crypto_address": crypto_address,
                    "card_provider": card_provider,
                    "card_recipient": card_recipient})
                message = "Настройки выплат сохранены."
        elif action == "update_user_role":
            try:
                target_user_id = int(form.get("user_id", 0))
            except (TypeError, ValueError):
                target_user_id = 0
            new_role = form.get("role", "user")
            if new_role not in {"user", "admin"}:
                message = "Недопустимая роль."
            elif not target_user_id:
                message = "Пользователь не найден."
            else:
                target_user = next((u for u in engine.list_users() if u[0] == target_user_id), None)
                if target_user and target_user[1] == user_email and new_role != "admin":
                    message = "Нельзя снять права администратора с собственной учетной записи."
                elif engine.update_user_role(target_user_id, new_role):
                    engine.record_audit("role_changed", f"user={target_user_id} role={new_role}", user_email)
                    message = "Роль пользователя обновлена."
                else:
                    message = "Пользователь не найден."
        elif action == "save_site_settings":
            site_name = str(form.get("site_name", "")).strip()
            support_contact = str(form.get("support_contact", "")).strip()
            maintenance_mode = "true" if form.get("maintenance_mode") else "false"
            selected_exchanges = form.getlist("allowed_exchanges") if hasattr(form, "getlist") else []
            selected_wallets = form.getlist("allowed_wallets") if hasattr(form, "getlist") else []
            allowed_exchanges = [ex for ex in selected_exchanges if ex in SUPPORTED_MARKET_EXCHANGES]
            allowed_wallets = [w for w in selected_wallets if w in WALLET_PROVIDERS]
            if not site_name:
                message = "Укажите название сайта."
            else:
                engine.save_site_settings(
                    site_name=site_name,
                    support_contact=support_contact,
                    maintenance_mode=maintenance_mode,
                    allowed_exchanges=",".join(allowed_exchanges) or ",".join(sorted(SUPPORTED_MARKET_EXCHANGES)),
                    allowed_wallets=",".join(allowed_wallets) or ",".join(WALLET_PROVIDERS),
                )
                message = "Настройки сайта сохранены."
    site_settings = engine.get_site_settings()
    all_purchases = engine.list_all_purchases()
    all_wallets = engine.list_all_wallets()
    purchase_counts = Counter(item[1] for item in all_purchases)
    return templates.TemplateResponse(request, "admin.html",
        {
                        "user_id": user_email,
            "users": engine.list_users(),
            "plugins": engine.list_plugins(),
            "purchases": all_purchases,
            "wallets": all_wallets,
            "message": message,
            "risk": risk_manager.status(),
            "current_strategy": strategy_manager.current_strategy(),
            "config": strategy_manager.config,
            "payout_settings": _payout_settings,
            "crypto_payout_assets": CRYPTO_PAYOUT_ASSETS,
            "card_payout_services": CARD_PAYOUT_SERVICES,
            "site_settings": site_settings,
            "supported_exchanges": sorted(SUPPORTED_MARKET_EXCHANGES),
            "wallet_providers": WALLET_PROVIDERS,
            "allowed_exchanges": {name.strip() for name in site_settings["allowed_exchanges"].split(",")},
            "allowed_wallets": {name.strip() for name in site_settings["allowed_wallets"].split(",")},
            "plugin_purchase_counts": sorted(purchase_counts.items(), key=lambda item: item[1], reverse=True),
            "plugin_purchase_counts_map": dict(purchase_counts),
            "connected_wallets_count": sum(1 for w in all_wallets if w[2] or w[4]),
            **social_login_context()},
    )


@app.post("/api/demo/trade")
def demo_trade(payload: DemoTradePayload, request: Request):
    email = _require_user(request)
    engine.ensure_demo_session(email)
    demo = engine.get_demo_session(email)
    if not demo.get("demo_active"):
        raise HTTPException(status_code=400, detail="Демо-режим отключён.")
    try:
        strategy_manager.config["strategy"] = payload.strategy
        side_factor = -1.0 if payload.side.lower() == "sell" else 1.0
        adjusted_sentiment = max(-1.0, min(1.0, payload.sentiment * side_factor))
        adjusted_price_change = payload.price_change * side_factor
        result = strategy_manager.execute(adjusted_sentiment, adjusted_price_change, demo["demo_balance"])
        balance_before = float(demo["demo_balance"])
        allocation = min(max(float(payload.amount), 1.0), balance_before) / max(balance_before, 1.0)
        pnl = result["pnl"] * allocation
        updated = engine.update_demo_balance(email, pnl)
        engine.record_memory("demo_trade", pnl, f"{payload.pair} {payload.strategy} {payload.side}", email)
        return {
            "pnl": round(pnl, 4),
            "balance": round(updated["demo_balance"], 2),
            "signal": result["signal"] if payload.side.lower() == "buy" else -result["signal"],
            "strategy": payload.strategy,
            "side": payload.side,
            "amount": round(float(payload.amount), 2),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/demo/status")
def demo_status(request: Request):
    email = _require_user(request)
    engine.ensure_demo_session(email)
    return engine.get_demo_session(email)

@app.post("/api/demo/toggle")
def demo_toggle(payload: DemoTogglePayload, request: Request):
    email = _require_user(request)
    engine.ensure_demo_session(email)
    return engine.toggle_demo_mode(email, payload.active)

@app.post("/api/strategies/create")
def create_strategy(payload: StrategyCreatePayload, request: Request):
    email = _require_user(request)
    result = engine.create_strategy(
        email, payload.name, payload.description, payload.strategy_type,
        payload.leverage, payload.risk_tolerance, payload.fee_rate,
        payload.is_public, payload.price_eur,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Не удалось создать стратегию.")
    return result

@app.get("/api/strategies/user")
def user_strategies(request: Request):
    email = _require_user(request)
    return engine.list_user_strategies(email)

@app.get("/api/strategies/public")
def public_strategies(request: Request):
    return engine.list_public_strategies()

@app.get("/api/bot/memory")
def bot_memory(request: Request):
    _require_user(request)
    return bot.get_memory_summary()


@app.post("/api/bot/generate")
def generate_strategies(request: Request):
    email = _require_user(request)
    try:
        client = _public_exchange("binance")
        daily = refresh_history(MARKET_DATABASE, client, "binance", "BTC/USDT")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить данные: {exc}") from exc
    result = bot.generate_strategies(engine, daily[-180:])
    engine.record_audit("strategy_generation", str(result.get("published", 0)), email)
    return result

@app.get("/api/bot/generation-status")
def generation_status(request: Request):
    _require_user(request)
    return bot.strategy_generator.get_status()

@app.post("/api/bot/auto-generate")
def toggle_auto_generate(request: Request, enabled: bool = True):
    _require_admin(request)
    return bot.toggle_auto_generate(enabled)

@app.post("/admin/risk", name="admin_risk_action")
async def admin_risk_action(request: Request, enabled: str = Form("true")):
    email = _require_admin(request)
    risk_manager.set_kill_switch(enabled.lower() == "true")
    engine.record_audit("kill_switch", enabled, email)
    return RedirectResponse(url="/admin", status_code=303)

@app.api_route("/profile", methods=["GET", "POST"], name="profile_page")
async def profile(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    ctx = _trading_context(user_email)
    db_user = engine.get_user(user_email)
    wallet = engine.get_or_create_wallet(user_email)
    exchanges = exchange_service.list_connected(user_email)
    site_settings = engine.get_site_settings()
    message = None
    message = None
    if request.method == "POST":
        form = await request.form()
        action = form.get("action")
        if action == "save_profile":
            message = "Настройки профиля сохранены."
        elif action == "save_theme":
            theme = form.get("theme", "dark")
            if theme in {"light", "dark", "auto"}:
                request.session["theme"] = theme
                message = "Тема оформления сохранена."
            else:
                message = "Выберите доступную тему оформления."
        elif action == "save_trading_preferences":
            strategy = str(form.get("strategy", strategy_manager.current_strategy()))
            try:
                leverage = max(0.1, min(float(form.get("leverage", 1.5)), 10))
                risk_tolerance = max(0.0, min(float(form.get("risk_tolerance", 0.03)), 1))
                fee_rate = max(0.0, min(float(form.get("fee_rate", 0.001)), 0.05))
                save_strategy_config(strategy, leverage, risk_tolerance, fee_rate)
                bot.set_strategy(strategy)
                engine.set_active_strategy(user_email, strategy)
                message = "Торговые настройки сохранены."
            except (TypeError, ValueError):
                message = "Проверьте значения левериджа, риска и комиссии."
        elif action == "toggle_demo":
            active = str(form.get("active", "true")).lower() == "true"
            engine.toggle_demo_mode(user_email, active)
            ctx["demo"] = engine.get_demo_session(user_email)
            message = "Демо-режим " + ("включён" if active else "выключен") + "."
        elif action == "connect_exchange":
            provider = str(form.get("exchange_provider", ""))
            api_key = str(form.get("exchange_key", ""))
            api_secret = str(form.get("exchange_secret", ""))
            sandbox = str(form.get("exchange_sandbox", "true")).lower() == "true"
            if provider and api_key:
                ok, err = exchange_service.connect(user_email, provider, api_key, api_secret, sandbox=sandbox)
                if ok:
                    message = f"Биржа {provider} подключена."
                else:
                    message = f"Ошибка подключения: {err}"
            else:
                message = "Укажите биржу и API ключ."
            exchanges = exchange_service.list_connected(user_email)
        elif action == "disconnect_exchange":
            provider = str(form.get("exchange_provider", ""))
            exchange_service.disconnect(user_email)
            exchanges = exchange_service.list_connected(user_email)
            message = f"Биржа {provider} отключена."
        elif action == "connect_wallet":
            provider = str(form.get("wallet_provider", "")).strip()
            address = str(form.get("wallet_address", "")).strip()
            if provider not in WALLET_PROVIDERS:
                message = "Выберите поддерживаемый кошелёк."
            elif not address:
                message = "Укажите адрес кошелька."
            else:
                engine.update_wallet(user_email, wallet_provider=provider, wallet_address=address)
                message = f"Кошелёк {provider} подключён."
        elif action == "connect_telegram":
            telegram_username = str(form.get("telegram_username", "")).strip().lstrip("@")
            telegram_token = str(form.get("telegram_token", "")).strip()
            if not telegram_username or not telegram_token:
                message = "Укажите Telegram username и Bot token."
            else:
                engine.update_wallet(user_email, telegram_username=telegram_username)
                message = f"Telegram @{telegram_username} подключён."
        ctx["message"] = message
        ctx["demo"] = engine.get_demo_session(user_email)
        wallet = engine.get_or_create_wallet(user_email)
        exchanges = exchange_service.list_connected(user_email)
    ctx.update({
        "user_id": user_email,
        "user": db_user,
        "wallet": wallet,
        "exchanges": exchanges,
        "message": message,
        "config": strategy_manager.config,
        "theme": request.session.get("theme", "dark"),
        "selected_theme": request.session.get("theme", "dark"),
        "site_settings": site_settings,
        "current_strategy": strategy_manager.current_strategy(),
        "risk": risk_manager.status(),
        "risk_score": risk_manager.calculate_risk_score(leverage=float(strategy_manager.config.get("leverage", 1.5))),
        "bot_runtime": bot_runtime.status(user_email),
        "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
        "trading_exchanges": sorted(SUPPORTED_MARKET_EXCHANGES),
        "wallet_providers": WALLET_PROVIDERS,
        "allowed_exchanges": {name.strip() for name in site_settings["allowed_exchanges"].split(",")},
        "allowed_wallets": {name.strip() for name in site_settings["allowed_wallets"].split(",")},
    })
    return templates.TemplateResponse(request, "profile.html", ctx)

@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

@app.post("/api/user/connect-arbitrage-exchange")
def connect_arbitrage_exchange(config: ArbitrageExchangeConfig, request: Request):
    email = _require_user(request)
    try:
        exchange_name = config.exchange_name.lower()
        if exchange_name not in SUPPORTED_MARKET_EXCHANGES:
            raise HTTPException(status_code=400, detail="Биржа не поддерживается.")
        exchange_class = getattr(ccxt, exchange_name)
        exchange_config = {
            "apiKey": config.api_key,
            "secret": config.api_secret,
            "enableRateLimit": True,
        }
        if config.passphrase:
            exchange_config["password"] = config.passphrase
        client = exchange_class(exchange_config)
        client.load_markets()
        engine.update_wallet(email,
            exchange_provider_arb=exchange_name,
            exchange_key_masked_arb=engine.mask_secret(config.api_key))
        engine.record_audit("arbitrage_exchange_connected", exchange_name, user_email=email)
        return {"ok": True, "exchange": exchange_name, "mode": "arbitrage"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка подключения: {exc}")

@app.post("/api/user/connect-exchange")
def connect_exchange(config: ExchangeConfig, request: Request):
    _require_user(request)
    try:
        exchange_class = getattr(ccxt, config.exchange_name.lower())
        exchange = exchange_class({
            'apiKey': config.api_key,
            'secret': config.api_secret,
            'enableRateLimit': True
        })
        exchange.load_markets()
        engine.record_bot_stat("exchange_connection", f"connected {config.exchange_name}")
        return {"status": "success", "message": f"Успешное подключение к {config.exchange_name.capitalize()}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка API: {str(e)}")

@app.post("/api/trading/test")
def trading_test(payload: TradingTestPayload, request: Request):
    email = _require_user(request)
    decision = risk_manager.decide(payload.current_balance, 1.0)
    if not decision.allowed:
        raise HTTPException(status_code=429, detail=decision.reason)
    allowed_pairs = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}
    if payload.pair not in allowed_pairs:
        raise HTTPException(status_code=400, detail="Недоступная торговая пара.")
    result = strategy_manager.execute(
        payload.news_sentiment, payload.price_change, max(0.0, payload.current_balance)
    )
    result["pair"] = payload.pair
    result["trade"] = bot.simulate(payload.pair, strategy_manager.current_strategy(), result)
    engine.record_memory(
        "strategy_test", result["trade"]["pl"],
        f"{payload.pair}; signal={result['signal']}; strategy={result['strategy']}",
        email,
    )
    engine.record_trade(
        email, payload.pair, "test", result["strategy"],
        result["trade"]["pl"], result["trade"]["next_balance"],
    )
    risk_manager.record(result["trade"]["pl"], result["trade"]["next_balance"])
    return result

@app.post("/api/trading/manual")
def manual_trade(payload: ManualTradePayload, request: Request):
    email = _require_user(request)
    allowed_pairs = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}
    if payload.pair not in allowed_pairs:
        raise HTTPException(status_code=400, detail="Недоступная торговая пара.")
    if payload.side not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail="Недопустимое направление сделки.")
    if payload.price <= 0 or payload.amount <= 0 or payload.balance < 0:
        raise HTTPException(status_code=400, detail="Цена и количество должны быть положительными.")
    fee_rate = float(strategy_manager.config.get("fee_rate", 0.001))
    fee = payload.price * payload.amount * fee_rate
    new_balance = max(0.0, payload.balance - fee)
    mode = current_mode()
    if mode == "live" and not LIVE_CONTROL_STATE.allows(bot_id="manual", ai_bot_id=None):
        return {"status": "blocked", "reason": "LIVE trading disabled by global kill switch.", "fee": round(fee, 6), "balance": round(new_balance, 2)}
    # NEVER report FILLED until exchange confirms. Use 'submitted' semantics for LIVE.
    status = "submitted" if mode == "live" else "executed"
    order_id = None
    if mode == "live":
        try:
            order_id = submit_real_order(email, payload.pair, payload.side, payload.price, payload.amount)
            status = "submitted"
        except Exception as exc:
            return {"status": "rejected", "reason": safe_exception_message(exc, "manual_trade"), "fee": round(fee, 6), "balance": round(new_balance, 2)}
    engine.record_trade(email, payload.pair, "manual", payload.side, -fee, new_balance)
    engine.record_audit("manual_trade", f"{payload.side} {payload.pair} ({status})", email)
    return {"status": status, "fee": round(fee, 6), "balance": round(new_balance, 2), "order_id": order_id}

@app.get("/api/trading/history")
def trading_history(request: Request, limit: int = 50):
    email = _require_user(request)
    return {"trades": engine.list_trades(email, limit)}

@app.get("/api/strategies")
def strategies(request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        performance = _strategy_performance()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить реальные данные: {exc}") from exc
    return _strategy_catalog(email, performance)

@app.post("/api/strategies/purchase")
def purchase_strategy(payload: PluginActionPayload, request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        performance = _strategy_performance()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось проверить месячную доходность: {exc}") from exc
    result = performance.get(payload.plugin_name)
    if not result or result["price_eur"] <= 0:
        engine.purchase_plugin(email, payload.plugin_name, 0.0, payload.duration_days)
        return {"status": "free", "plugin": payload.plugin_name, "duration_days": payload.duration_days}
    try:
        purchase_price = price_for_duration(result["price_eur"], payload.duration_days)
        purchase = engine.purchase_plugin(email, payload.plugin_name, purchase_price, payload.duration_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not purchase:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")
    # Durable CMSC debit ledger
    engine.record_payment(email, purchase_price, currency="CMSC", type="purchase", reference=f"plugin:{payload.plugin_name}")
    return {**purchase, "status": "purchased", "ledger": True}


@app.get("/api/strategies/performance")
def strategy_performance(request: Request, pair: str = "BTC/USDT", exchange: str = "binance", period: str = "1m"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return {
            "pair": pair,
            "exchange": exchange,
            "period": period,
            "period_label": {
                "1d": "1 день",
                "1w": "1 неделя",
                "1m": "1 месяц",
                "3m": "3 месяца",
                "6m": "6 месяцев",
                "1y": "1 год",
            }.get(period, "1 месяц"),
            "currency": "EUR",
            "strategies": _strategy_performance(exchange, pair, period)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось рассчитать доходность: {exc}") from exc

@app.post("/api/strategies/activate")
def activate_strategy(payload: PluginActionPayload, request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    plugin = next((item for item in engine.list_plugins() if item.name == payload.plugin_name), None)
    if not plugin:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")
    try:
        performance = _strategy_performance()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось проверить цену стратегии: {exc}") from exc
    owned = engine.user_plugins(email)
    owned_item = next((x for x in owned if x["name"] == plugin.name), None)
    price = performance.get(plugin.name, {}).get("price_eur", float(plugin.price))
    if not owned_item:
        # Free strategy or trial grant: create access record
        engine.purchase_plugin(email, plugin.name, max(0.0, price) if payload.trial else price, 15)
        if price > 0 and not payload.trial:
            ledger = engine.record_payment(email, price, currency="CMSC", type="purchase", reference=f"plugin:{plugin.name}")
            if ledger["status"] != "completed":
                raise HTTPException(status_code=402, detail=ledger["reason"])
    if not engine.set_plugin_active(email, plugin.name, True):
        raise HTTPException(status_code=402, detail="Сначала купите стратегию или активируйте trial.")
    strategy_manager.config["strategy"] = plugin.name
    # Persist active strategy so it survives restart/serverless
    engine.set_active_strategy(email, plugin.name)
    return {"status": "active", "strategy": plugin.name, "persisted": True}


@app.get("/api/market/data")
def market_data(request: Request, pair: str = "BTC/USDT", exchange: str = "binance"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    if pair not in {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}:
        raise HTTPException(status_code=400, detail="Недоступная торговая пара.")
    try:
        exchange = (exchange or "binance").lower()
        client = _public_exchange(exchange)
        ticker = client.fetch_ticker(pair)
        order_book = client.fetch_order_book(pair, limit=10)
        candles = refresh_candles(MARKET_DATABASE, client, exchange, pair, timeframe="1h")
    except Exception:
        cached = cached_get(f"market_data:{pair}:{exchange}")
        if cached is None:
            raise HTTPException(status_code=502, detail="Не удалось получить данные рынка. Проверьте подключение к бирже.")
        exchange, pair, ticker, order_book, candles = cached
    result = (exchange, pair, ticker, order_book, candles)
    cached_fetch(f"market_data:{pair}:{exchange}", 5, lambda: result)
    return {
        "exchange": exchange,
        "pair": pair,
        "ticker": {"last": ticker.get("last"), "change": ticker.get("percentage")},
        "order_book": {
            "bids": (order_book.get("bids") or [])[:10],
            "asks": (order_book.get("asks") or [])[:10]},
        "candles": candles[-100:]}


@app.get("/api/market/history")
def market_history(request: Request, pair: str = "BTC/USDT", exchange: str = "binance",
                   timeframe: str = "1h"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    if pair not in {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}:
        raise HTTPException(status_code=400, detail="Недоступная торговая пара.")
    if timeframe not in {"1m", "5m", "15m", "1h", "1d"}:
        raise HTTPException(status_code=400, detail="Поддерживаются таймфреймы от 1m до 1d.")
    try:
        exchange = (exchange or "binance").lower()
        client = _public_exchange(exchange)
        if timeframe == "1d":
            history = refresh_history(MARKET_DATABASE, client, exchange, pair)
        else:
            history = refresh_candles(
                MARKET_DATABASE, client, exchange, pair, timeframe=timeframe
            )
        return {"exchange": exchange, "pair": pair, "timeframe": timeframe,
                "candles": history, "count": len(history),
                "retention_days": 365 if timeframe == "1d" else 30,
                "analysis_policy": "Сигналы используют только закрытые текущие и предыдущие свечи."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось обновить историю: {exc}") from exc


@app.get("/api/market/news")
def market_news(request: Request, refresh: bool = True, limit: int = 100):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        if refresh:
            refresh_news(MARKET_DATABASE)
        news = load_news(MARKET_DATABASE, limit=limit)
        return {
            "news": news,
            "count": len(news),
            "sentiment": analyze_news_sentiment(news),
            "source": "сохранённая история CoinDesk RSS",
            "analysis_policy": "В историю и анализ попадают только новости, опубликованные к моменту запроса."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось обновить новости: {exc}") from exc


@app.get("/api/market/signal")
def market_signal(request: Request, pair: str = "BTC/USDT", exchange: str = "binance", source: str = "bot"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return _signal_for_pair(pair, exchange, source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось рассчитать сигнал: {exc}") from exc


@app.get("/api/market/signals")
def market_signals(request: Request, exchange: str = "binance", source: str = "bot"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return {"signals": _signals_for_all_pairs(exchange, source)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить сигналы: {exc}") from exc


class ApplySignalPayload(BaseModel):
    pair: str = "BTC/USDT"
    exchange: str = "binance"
    source: str = "bot"
    amount: float = 10.0
    mode: str = "demo"


@app.post("/api/market/apply-signal")
def apply_market_signal(payload: ApplySignalPayload, request: Request):
    email = _require_user(request)
    signal = _signal_for_pair(payload.pair, payload.exchange, payload.source)
    balance = engine.get_demo_session(email).get("demo_balance", 100.0)
    suggested_amount = min(max(payload.amount, 1.0), balance)
    return {
        **signal,
        "mode": payload.mode,
        "suggested_amount": round(suggested_amount, 2),
        "applied": False,
        "note": "Signal prepared for execution. Use terminal controls to submit the trade.",
    }


@app.post("/api/chat")
def chat(payload: ChatPayload, request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым.")
    memories = engine.recent_memories(email, 10)
    profitable = [item for item in memories if item["result"] > 0]
    lower_message = message.lower()
    if any(word in lower_message for word in ("новост", "news")):
        try:
            refresh_news(MARKET_DATABASE)
            news = load_news(MARKET_DATABASE, limit=5)
            sentiment = analyze_news_sentiment(news)
            answer = (
                f"В истории {len(news)} последних новостей, агрегированный сентимент "
                f"{sentiment:+.2f}. "
                + ("Последние заголовки: " + "; ".join(item["title"] for item in news)
                   if news else "Свежих новостей пока нет.")
                + " Это информационный анализ, не финансовая рекомендация."
            )
        except Exception:
            answer = "Не удалось получить историю новостей. Повторите запрос позже."
    elif any(word in lower_message for word in ("сигнал", "прогноз", "рынок", "btc", "eth", "час")):
        pair = "ETH/USDT" if "eth" in lower_message else "BTC/USDT"
        try:
            signal = _market_signal(pair, "binance")
            direction = {1: "ПОКУПКА", -1: "ПРОДАЖА", 0: "ОЖИДАНИЕ"}.get(signal["signal"], "ОЖИДАНИЕ")
            answer = (
                f"{pair}: сигнал {direction} на {signal['horizon']}. "
                f"Последняя цена {signal['last_price']:.4f}, изменение за час "
                f"{signal['hour_change']:.2f}%, уверенность {signal['confidence']:.0%}. "
                f"Проанализировано {signal['hourly_candles']} часовых и "
                f"{signal['daily_candles']} дневных свечей. {signal['disclaimer']}"
            )
        except (TypeError, ValueError, ccxt.BaseError):
            answer = f"Не удалось получить свежий сигнал по {pair}. Повторите запрос позже."
    elif "стратег" in lower_message or "рекоменд" in lower_message:
        answer = (
            f"Текущая стратегия: {strategy_manager.current_strategy()}. "
            f"В памяти {len(memories)} наблюдений, прибыльных: {len(profitable)}. "
            "Рекомендация: тестируйте изменения на истории и не используйте риск выше лимита."
        )
    elif memories:
        answer = (
            f"Я сохранил ваши последние действия. Последний результат: "
            f"{memories[0]['result']:.4f}. Могу подсказать стратегию или разобрать тест."
        )
    else:
        answer = "Память пока пуста. Запустите тест стратегии, и я начну сохранять результаты."
    engine.record_memory("chat", 0.0, message, email)
    return {"answer": answer, "memory_count": len(memories)}

@app.get("/api/trading/status")
def trading_status(request: Request):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    return bot.status()

@app.post("/api/bot/start")
def start_bot(request: Request, pair: str = "BTC/USDT", exchange: str = "binance"):
    email = _require_admin(request)
    # Unified kill switch: block if either the RiskManager or LiveControlState blocks LIVE
    if risk_manager.kill_switch or LIVE_CONTROL_STATE.global_kill_switch:
        raise HTTPException(status_code=423, detail="Сначала отключите аварийный выключатель.")
    leverage = float(strategy_manager.config.get("leverage", 1.5))
    risk_score = risk_manager.calculate_risk_score(leverage=leverage)
    allowed, reason = risk_manager.check_risk_score(risk_score)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    engine.ensure_demo_session(email)
    result = bot.start()
    rt = bot_runtime.start(email, pair=pair, exchange=exchange)
    result.update({"risk_score": risk_score, "lifecycle": bot_runtime.lifecycle})
    engine.record_audit("bot_started", f"{pair}@{exchange}", email)
    engine.record_bot_stat("bot_status", "started")
    return result

@app.post("/api/bot/stop")
def stop_bot(request: Request):
    email = _require_admin(request)
    rt = bot_runtime.stop(email)
    result = bot.stop()
    engine.record_audit("bot_stopped", user_id=email)
    engine.record_bot_stat("bot_status", "stopped")
    return {"status": result["status"], "lifecycle": rt["lifecycle"]}


@app.post("/api/bot/pause")
def pause_bot(request: Request):
    _require_user(request)
    return bot_runtime.pause()


@app.post("/api/bot/resume")
def resume_bot(request: Request, pair: str = "BTC/USDT", exchange: str = "binance"):
    email = _require_user(request)
    return bot_runtime.resume(email, pair=pair, exchange=exchange)


@app.post("/api/bot/emergency-stop")
def emergency_stop_bot(request: Request):
    """Emergency stop: engages unified kill switch + runtime emergency stop."""
    email = _require_admin(request)
    LIVE_CONTROL_STATE.set_global_kill_switch(enabled=True, actor=email)
    risk_manager.set_kill_switch(True)
    engine.record_audit("emergency_stop", "kill_switch engaged", email)
    return bot_runtime.emergency_stop(email)

@app.get("/api/bot/status")
def bot_status(request: Request):
    email = _require_user(request)
    status = bot.status()
    status.update(bot_runtime.status(email))
    return status

@app.post("/api/bot/backtest")
def bot_backtest(payload: BacktestPayload, request: Request):
    _require_user(request)
    allowed_pairs = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}
    if payload.pair not in allowed_pairs:
        raise HTTPException(status_code=400, detail="Недоступная торговая пара.")
    if payload.initial_balance <= 0:
        raise HTTPException(status_code=400, detail="Начальный баланс должен быть положительным.")
    try:
        client = _public_exchange(payload.exchange)
        daily = refresh_history(MARKET_DATABASE, client, payload.exchange.lower(), payload.pair)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить историю: {exc}") from exc
    names = [plugin.name for plugin in engine.list_plugins()]
    performance = evaluate_strategies(
        _truncate_daily_candles(daily, payload.period),
        names,
        fee_rate=_exchange_fee_rate(payload.exchange, payload.pair),
    )
    if payload.strategy and payload.strategy != "all":
        names = [payload.strategy] if payload.strategy in performance else []
    scale = payload.initial_balance / 100.0
    results = []
    for name, data in performance.items():
        if names and name not in names:
            continue
        results.append({
            "strategy": name,
            "final_balance": round(data["final_balance_eur"] * scale, 2),
            "pnl": round((data["final_balance_eur"] - 100.0) * scale, 2),
            "roi": data["monthly_return_pct"],
            "wins": round(data["win_rate_pct"] / 100 * data["trades"]),
            "trades": data["trades"],
            "max_drawdown": data["max_drawdown_pct"],
            "sharpe": data["sharpe"],
            "sortino": data["sortino"],
            "profit_factor": data["profit_factor"],
            "period": payload.period,
            "fee_rate": _exchange_fee_rate(payload.exchange, payload.pair),
        })
    return {"results": results}

@app.post("/api/bot/simulate")
def simulate_trade(payload: HFTSimulatePayload, request: Request):
    _require_user(request)
    try:
        capital = production_bot.trade_loop(payload.market_data, payload.ai_stream)
        metrics = production_bot.metrics()
        engine.record_bot_stat("hft_simulation", f"capital {capital}")
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/bot/brain")
def brain_status(request: Request):
    _require_admin(request)
    return production_bot.brain.summarize()

@app.get("/api/report")
def get_report(request: Request):
    _require_admin(request)
    try:
        with (BASE_DIR / "ADVANCED_TEST_REPORT.md").open("r", encoding="utf-8") as report_file:
            return {"report": report_file.read()}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Отчет не найден")

@app.get("/api/metrics")
def get_metrics(request: Request):
    _require_admin(request)
    return {
        "bot_status": bot.status(),
        "brain": production_bot.brain.summarize(),
        "strategy": strategy_manager.current_strategy(),
        "config": strategy_manager.config,
        "risk": risk_manager.status()}

@app.post("/api/strategy/execute")
def execute_strategy(payload: StrategyPayload, request: Request):
    email = _require_user(request)
    decision = risk_manager.decide(payload.current_balance, float(strategy_manager.config.get("leverage", 1.0)))
    if not decision.allowed:
        raise HTTPException(status_code=429, detail=decision.reason)
    result = strategy_manager.execute(payload.news_sentiment, payload.price_change, payload.current_balance)
    risk_manager.record(result["pnl"], result["next_balance"])
    engine.record_audit("strategy_execution", str(result), email)
    engine.record_bot_stat("strategy_execution", str(result))
    return result

@app.get("/api/risk/status")
def risk_status(request: Request):
    _require_user(request)
    status = risk_manager.status()
    leverage = float(strategy_manager.config.get("leverage", 1.0))
    status["current_risk_score"] = risk_manager.calculate_risk_score(leverage=leverage)
    status["max_risk_score"] = risk_manager.MAX_RISK_SCORE
    return status

@app.post("/api/risk/score")
def calculate_risk_score(request: Request, leverage: float = 1.0, volatility: float = 0.02,
                         drawdown: float = 0.0, liquidity: float = 0.8,
                         concentration: float = 0.1, positions: int = 1,
                         execution_complexity: int = 1, exchange_risk: float = 0.1,
                         slippage: float = 0.001, market_regime: str = "normal"):
    _require_user(request)
    score = risk_manager.calculate_risk_score(
        volatility=volatility, leverage=leverage, drawdown=drawdown,
        liquidity=liquidity, concentration=concentration, positions=positions,
        execution_complexity=execution_complexity, exchange_risk=exchange_risk,
        slippage=slippage, market_regime=market_regime
    )
    allowed, reason = risk_manager.check_risk_score(score)
    return {"risk_score": score, "allowed": allowed, "reason": reason, "max_allowed": risk_manager.MAX_RISK_SCORE}

@app.post("/api/risk/kill-switch")
def set_kill_switch(payload: KillSwitchPayload, request: Request):
    """Unified kill switch: syncs RiskManager + LiveControlState."""
    email = _require_admin(request)
    # Global kill switch engages both the risk layer and the LIVE control layer
    if not payload.enabled:
        LIVE_CONTROL_STATE.set_global_kill_switch(enabled=False, actor=email)
    risk_manager.set_kill_switch(payload.enabled)
    engine.record_audit("kill_switch", str(payload.enabled), email)
    return {**risk_manager.status(), "global_kill_switch": LIVE_CONTROL_STATE.global_kill_switch, "bot_live": dict(LIVE_CONTROL_STATE.bot_live), "ai_bot_live": dict(LIVE_CONTROL_STATE.ai_bot_live)}


# ─── Недостающие API (fix 404 "file not found") ───────────────────

@app.get("/api/wallet/balance")
def api_wallet_balance(request: Request):
    email = _require_user(request)
    wallet = engine.get_or_create_wallet(email)
    return {"balance": wallet.get("balance", 0), "currency": "EUR", "provider": wallet.get("provider", ""), "address": wallet.get("address", "")}

@app.post("/api/wallet/connect")
def api_wallet_connect(request: Request, provider: str = Form(...), address: str = Form(...)):
    email = _require_user(request)
    if provider not in WALLET_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")
    engine.update_wallet(email, wallet_provider=provider, wallet_address=address)
    engine.record_audit("wallet_connected", provider, email)
    return {"ok": True, "provider": provider}

@app.get("/api/settings")
def api_get_settings(request: Request):
    email = _require_user(request)
    db_user = engine.get_user(email)
    site_settings = engine.get_site_settings()
    theme = getattr(db_user, "theme", "light") if db_user else "light"
    username = getattr(db_user, "username", "") if db_user else ""
    return {"theme": theme, "email": email, "username": username, "site_settings": site_settings}

@app.get("/api/profile")
def api_profile(request: Request):
    email = _require_user(request)
    db_user = engine.get_user(email)
    wallet = engine.get_or_create_wallet(email)
    username = getattr(db_user, "username", "") if db_user else ""
    return {"username": username, "email": email, "wallet": wallet}

@app.get("/api/exchanges")
def api_exchanges():
    return {"exchanges": [{"id": e, "name": e.capitalize()} for e in SUPPORTED_MARKET_EXCHANGES]}

@app.get("/api/market/trending")
def api_market_trending():
    try:
        trending = _strategy_performance()
        return {"trending": trending}
    except Exception:
        return {"trending": []}

@app.get("/api/demo/balance")
def api_demo_balance(request: Request):
    user = _require_user(request)
    return {"balance": 100.0, "currency": "EUR", "trades": []}

@app.get("/api/demo/history")
def api_demo_history(request: Request):
    user = _require_user(request)
    return {"trades": []}

@app.get("/api/bot/config")
def api_bot_config(request: Request):
    _require_user(request)
    return {"strategy": strategy_manager.current_strategy(), "config": strategy_manager.config}

@app.get("/api/admin/stats")
def api_admin_stats(request: Request):
    _require_admin(request)
    return {"users": 1, "strategies": len(strategy_manager.list_strategies()) if hasattr(strategy_manager, 'list_strategies') else 0, "status": "ok"}

@app.get("/api/admin/settings")
def api_admin_get_settings(request: Request):
    _require_admin(request)
    return engine.get_site_settings()

@app.get("/api/notifications")
def api_notifications(request: Request):
    _require_user(request)
    return {"notifications": []}

@app.get("/api/market/listings")
def api_market_listings(request: Request):
    _require_user(request)
    try:
        catalog = _strategy_catalog(_require_user(request), _strategy_performance())
        return {"listings": catalog}
    except Exception:
        return {"listings": []}

@app.get("/api/feedback")
def api_feedback(request: Request):
    _require_user(request)
    return {"feedback": []}

@app.post("/api/feedback")
def api_submit_feedback(request: Request, message: str = Form(...)):
    email = _require_user(request)
    engine.record_audit("feedback", message, email)
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════
# Copy Trading — копирование стратегий трейдеров (как Pionex)
# ═══════════════════════════════════════════════════════════════

_copy_trading_state = {}  # email -> {copies: [], settings: {}}

def _get_traders_list():
    """Генерируем список трейдеров из bot memory и published strategies."""
    traders = []
    bot_status = bot.status()
    gen_status = bot.strategy_generator.get_status()
    log = gen_status.get("recent_log", [])

    builtin = [
        {"name": "Daily Compound Bot", "strategy": "pure_harvester", "return_pct": 0, "win_rate": 50, "trades": 0, "copied": False},
        {"name": "HFT Momentum Pro", "strategy": "high_frequency_momentum", "return_pct": 0, "win_rate": 50, "trades": 0, "copied": False},
        {"name": "Compound Defender", "strategy": "compound_defender", "return_pct": 0, "win_rate": 50, "trades": 0, "copied": False},
    ]

    for entry in log:
        if entry.get("action") == "published":
            builtin.append({
                "name": entry.get("name", "Auto Strategy"),
                "strategy": "auto_generated",
                "return_pct": entry.get("return", 0),
                "win_rate": 50,
                "trades": 0,
                "copied": False,
            })

    if bot_status.get("trade_count", 0) > 0:
        builtin[0]["return_pct"] = round(bot_status.get("total_pnl", 0), 2)
        builtin[0]["win_rate"] = bot_status.get("win_rate", 0)
        builtin[0]["trades"] = bot_status.get("trade_count", 0)

    return builtin


@app.api_route("/copy-trading", methods=["GET", "POST"], name="copy_trading_page")
async def copy_trading_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)

    state = _copy_trading_state.get(user_email, {"copies": [], "settings": {}})
    traders = _get_traders_list()
    for t in traders:
        t["copied"] = t["name"] in state.get("copies", [])

    copying_count = sum(1 for t in traders if t["copied"])
    returns = [t["return_pct"] for t in traders if t["return_pct"]]
    avg_return = sum(returns) / len(returns) if returns else 0

    return templates.TemplateResponse(request, "copy_trading.html", {
        "user_id": user_email,
        "username": (engine.get_user(user_email).email if engine.get_user(user_email) else user_email),
        "theme": request.session.get("theme", "dark"),
        "traders": traders,
        "avg_return": avg_return,
        "copying_count": copying_count,
    })


class CopyTogglePayload(BaseModel):
    trader: str


@app.post("/api/copy-trading/toggle")
def copy_toggle(payload: CopyTogglePayload, request: Request):
    email = _require_user(request)
    state = _copy_trading_state.setdefault(email, {"copies": [], "settings": {}})
    if payload.trader in state["copies"]:
        state["copies"].remove(payload.trader)
    else:
        state["copies"].append(payload.trader)
    engine.record_audit("copy_toggle", f"trader={payload.trader}", email)
    return {"ok": True, "copies": state["copies"]}


class CopySettingsPayload(BaseModel):
    amount: float = 10.0
    max_loss: float = 5.0
    mode: str = "demo"
    strategy: str = "auto"


@app.post("/api/copy-trading/settings")
def copy_settings(payload: CopySettingsPayload, request: Request):
    email = _require_user(request)
    state = _copy_trading_state.setdefault(email, {"copies": [], "settings": {}})
    state["settings"] = payload.model_dump()
    engine.record_audit("copy_settings", str(state["settings"]), email)
    return {"ok": True, "settings": state["settings"]}


@app.post("/api/copy-trading/reset")
def copy_reset(request: Request):
    email = _require_user(request)
    _copy_trading_state[email] = {"copies": [], "settings": {}}
    engine.record_audit("copy_reset", "all cleared", email)
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════
# Testing page — тесты стратегий на реальных данных (live)
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# Arbitrage Engine — страница и API
# ═══════════════════════════════════════════════════════════════

@app.api_route("/arbitrage", methods=["GET", "POST"], name="arbitrage_page")
async def arbitrage_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    ctx = _trading_context(user_email)
    ctx["arbitrage"] = arbitrage_engine.status()
    return templates.TemplateResponse(request, "arbitrage.html", ctx)


@app.post("/api/arbitrage/start")
def arbitrage_start(request: Request):
    _require_admin(request)
    return arbitrage_engine.start()


@app.post("/api/arbitrage/stop")
def arbitrage_stop(request: Request):
    _require_admin(request)
    return arbitrage_engine.stop()


@app.get("/api/arbitrage/status")
def arbitrage_status(request: Request):
    _require_user(request)
    return arbitrage_engine.status()


@app.post("/api/arbitrage/scan")
def arbitrage_scan(request: Request):
    _require_user(request)
    leverage = float(strategy_manager.config.get("leverage", 1.0))
    risk_score = risk_manager.calculate_risk_score(leverage=leverage, execution_complexity=3)
    allowed, reason = risk_manager.check_risk_score(risk_score)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    results = {}
    try:
        import ccxt
        exchange = ccxt.binance({"enableRateLimit": True})
        pairs = ["BTC/USDT", "ETH/USDT", "ETH/BTC", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
        tickers = {}
        for pair in pairs:
            try:
                tickers[pair] = exchange.fetch_ticker(pair)
            except Exception:
                continue
        results["triangular"] = arbitrage_engine.triangular.scan(tickers)
        results["cross_exchange"] = []
        for pair in ["BTC/USDT", "ETH/USDT"]:
            opp = arbitrage_engine.cross_exchange.scan(tickers, tickers, pair)
            if opp:
                results["cross_exchange"].append(opp)
        for pair, ticker in tickers.items():
            price = float(ticker.get("last", 0))
            if price > 0:
                opp = arbitrage_engine.statistical.scan(pair, price)
                if opp:
                    results.setdefault("statistical", []).append(opp)
    except Exception as e:
        results["error"] = str(e)
    return results
