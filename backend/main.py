from pathlib import Path
import os
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
import ccxt

from .admin import router as admin_router
from .bot import HFTBot
from .cms_core import CMSEngine
from .hft_brain import CMSProductionHFTBot
from .modules.strategy_manager import StrategyManager
from .market_history import ensure_table, load_candles, refresh_candles, load_history, refresh_history

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Daily Compound Harvester CMS", version="1.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "development-only-change-me"),
    max_age=3600,
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")
app.include_router(admin_router)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def template_url_for(name: str, **values):
    if name == "static" and "filename" in values:
        values["path"] = values.pop("filename")
    return app.url_path_for(name, **values)

templates.env.globals["url_for"] = template_url_for
engine = CMSEngine()
bot = HFTBot()
production_bot = CMSProductionHFTBot()
strategy_manager = StrategyManager()
MARKET_DATABASE = str(BASE_DIR / "cms_v12.db")
SUPPORTED_MARKET_EXCHANGES = {"binance", "bybit", "kraken", "okx", "bitfinex"}

class ExchangeConfig(BaseModel):
    exchange_name: str
    api_key: str
    api_secret: str

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

class ChatPayload(BaseModel):
    message: str


def _public_exchange(name: str):
    exchange_name = (name or "binance").strip().lower()
    if exchange_name not in SUPPORTED_MARKET_EXCHANGES:
        raise ValueError("Неподдерживаемая публичная биржа.")
    exchange_class = getattr(ccxt, exchange_name, None)
    if exchange_class is None:
        raise ValueError("Биржа недоступна в установленной версии CCXT.")
    return exchange_class({"enableRateLimit": True, "timeout": 15000})


def _market_signal(pair: str, exchange_name: str):
    exchange = _public_exchange(exchange_name)
    candles = refresh_candles(MARKET_DATABASE, exchange, exchange_name, pair)
    daily = refresh_history(MARKET_DATABASE, exchange, exchange_name, pair)
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
        "disclaimer": "Сигнал информационный и не является гарантией доходности.",
    }

class PluginActionPayload(BaseModel):
    plugin_name: str

@app.get("/", name="index")
async def serve_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "user_id": request.session.get("user_email")})

@app.get("/home", name="home")
async def home(request: Request):
    return await serve_root(request)

@app.get("/login", name="login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "message": None, "user_id": request.session.get("user_email")})

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    # username field may contain email
    user = engine.secure_login(username, password)
    if user:
        request.session["user_email"] = user.email
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "message": "Неверный логин или пароль.", "user_id": None})

@app.get("/register", name="register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "message": None, "user_id": request.session.get("user_email")})

@app.post("/register")
async def register_submit(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    if password != confirm_password:
        return templates.TemplateResponse("register.html", {"request": request, "message": "Пароли не совпадают.", "user_id": None})
    try:
        user = engine.create_user(email, password)
        request.session["user_email"] = user.email
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "message": f"Ошибка регистрации: {e}", "user_id": None})

@app.get("/forgot-password", name="forgot_password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "message": None, "user_id": request.session.get("user_email")})

@app.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...)):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "Инструкции по восстановлению пароля отправлены на указанный email.", "user_id": request.session.get("user_email")})

@app.api_route("/dashboard", methods=["GET", "POST"], name="dashboard")
async def dashboard(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    message = None
    if request.method == "POST":
        form = await request.form()
        if form.get("action") == "save_theme" and form.get("theme") in {"light", "dark"}:
            request.session["theme"] = form["theme"]
            message = "Тема оформления сохранена."
    user = engine.get_user(user_email)
    username = user.email if user else user_email
    balance = "—"
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": username,
            "email": user_email,
            "balance": balance,
            "wallet": {"balance": 0.0, "provider": None, "address": None, "credits": 0.0},
            "user_id": user_email,
            "theme": request.session.get("theme", "light"),
            "selected_theme": request.session.get("theme", "light"),
            "message": message,
            "memories": engine.recent_memories(user_email, 5),
        },
    )

@app.api_route("/marketplace", methods=["GET", "POST"], name="marketplace")
async def marketplace(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    plugin_message = None
    if request.method == "POST":
        form = await request.form()
        if form.get("action") == "buy_plugin":
            purchase = engine.purchase_plugin(user_email, str(form.get("plugin_name", "")))
            plugin_message = (
                "Стратегия добавлена в ваши покупки."
                if purchase else "Стратегия не найдена."
            )
    return templates.TemplateResponse(
        "marketplace.html",
        {
            "request": request,
            "user_id": user_email,
            "wallet": {"balance": 0.0, "credits": 0.0},
            "internal_currency": "CMS Credits (CMSC)",
            "exchanges": [],
            "wallets": [],
            "plugins": [
                {"id": plugin.id, "name": plugin.name, "price": plugin.price,
                 "description": plugin.description}
                for plugin in engine.list_plugins()
            ],
            "purchases": engine.user_plugins(user_email),
            "message": None,
            "exchange_info": None,
            "plugin_message": plugin_message,
        },
    )

@app.get("/bot-management", name="bot_management")
async def bot_management(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "bot_management.html",
        {
            "request": request,
            "user_id": user_email,
            "bot_status": bot.status(),
            "current_strategy": strategy_manager.current_strategy(),
            "config": strategy_manager.config,
            "message": None,
            "manual_trade_result": None,
            "balance_history": [{"time": "start", "value": 100}],
            "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
        },
    )

@app.get("/wallet", name="wallet_page")
async def wallet_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "wallet.html",
        {
            "request": request,
            "user_id": user_email,
            "wallet": {"balance": 0.0, "credits": 0.0},
            "internal_currency": "CMS Credits (CMSC)",
            "message": None,
        },
    )

@app.get("/admin", name="admin_panel")
async def admin_panel(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user_id": user_email,
            "users": [],
            "plugins": engine.list_plugins(),
            "purchases": [],
            "wallets": [],
            "message": None,
        },
    )

@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

@app.post("/api/user/connect-exchange")
def connect_exchange(config: ExchangeConfig):
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
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
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
        request.session.get("user_email"),
    )
    return result

@app.get("/api/strategies")
def strategies(request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    purchased = {item["name"]: item["active"] for item in engine.user_plugins(email)}
    return [
        {"name": plugin.name, "price": plugin.price, "description": plugin.description,
         "available": plugin.price == 0 or plugin.name in purchased,
         "active": purchased.get(plugin.name, plugin.price == 0)}
        for plugin in engine.list_plugins()
    ]

@app.post("/api/strategies/purchase")
def purchase_strategy(payload: PluginActionPayload, request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    purchase = engine.purchase_plugin(email, payload.plugin_name)
    if not purchase:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")
    return purchase

@app.post("/api/strategies/activate")
def activate_strategy(payload: PluginActionPayload, request: Request):
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    plugin = next((item for item in engine.list_plugins() if item.name == payload.plugin_name), None)
    if not plugin:
        raise HTTPException(status_code=404, detail="Стратегия не найдена.")
    if plugin.price > 0 and not engine.set_plugin_active(email, plugin.name, True):
        raise HTTPException(status_code=402, detail="Сначала купите стратегию.")
    strategy_manager.config["strategy"] = plugin.name
    return {"status": "active", "strategy": plugin.name}


@app.get("/api/market/history")
def market_history(request: Request, pair: str = "BTC/USDT", exchange: str = "binance",
                   timeframe: str = "1h"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    if pair not in {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}:
        raise HTTPException(status_code=400, detail="Недоступная торговая пара.")
    if timeframe not in {"1h", "1d"}:
        raise HTTPException(status_code=400, detail="Поддерживаются таймфреймы 1h и 1d.")
    try:
        client = _public_exchange(exchange)
        if timeframe == "1d":
            history = refresh_history(MARKET_DATABASE, client, exchange, pair)
        else:
            history = refresh_candles(MARKET_DATABASE, client, exchange, pair)
        return {"exchange": exchange, "pair": pair, "timeframe": timeframe,
                "candles": history, "count": len(history),
                "retention_days": 365 if timeframe == "1d" else 30,
                "analysis_policy": "Сигналы используют только закрытые текущие и предыдущие свечи."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось обновить историю: {exc}") from exc


@app.get("/api/market/signal")
def market_signal(request: Request, pair: str = "BTC/USDT", exchange: str = "binance"):
    if not request.session.get("user_email"):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    try:
        return _market_signal(pair, exchange)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось рассчитать сигнал: {exc}") from exc


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
    if any(word in lower_message for word in ("сигнал", "прогноз", "рынок", "btc", "eth", "час")):
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
        except (TypeError, ValueError, ccxt.BaseError) as exc:
            answer = f"Не удалось получить свежий сигнал по {pair}: {exc}"
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
def start_bot():
    result = bot.start()
    engine.record_bot_stat("bot_status", "started")
    return result

@app.post("/api/bot/stop")
def stop_bot():
    result = bot.stop()
    engine.record_bot_stat("bot_status", "stopped")
    return result

@app.get("/api/bot/status")
def bot_status():
    return bot.status()

@app.post("/api/bot/simulate")
def simulate_trade(payload: HFTSimulatePayload):
    try:
        capital = production_bot.trade_loop(payload.market_data, payload.ai_stream)
        metrics = production_bot.metrics()
        engine.record_bot_stat("hft_simulation", f"capital {capital}")
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/bot/brain")
def brain_status():
    return production_bot.brain.summarize()

@app.get("/api/report")
def get_report():
    try:
        with (BASE_DIR / "ADVANCED_TEST_REPORT.md").open("r", encoding="utf-8") as report_file:
            return {"report": report_file.read()}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Отчет не найден")

@app.get("/api/metrics")
def get_metrics():
    return {
        "bot_status": bot.status(),
        "brain": production_bot.brain.summarize(),
        "strategy": strategy_manager.current_strategy(),
        "config": strategy_manager.config
    }

@app.post("/api/strategy/execute")
def execute_strategy(payload: StrategyPayload):
    result = strategy_manager.execute(payload.news_sentiment, payload.price_change, payload.current_balance)
    engine.record_bot_stat("strategy_execution", str(result))
    return result
