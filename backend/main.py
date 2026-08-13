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
templates.env.globals['url_for'] = app.url_path_for
engine = CMSEngine()
bot = HFTBot()
production_bot = CMSProductionHFTBot()
strategy_manager = StrategyManager()

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
        },
    )

@app.get("/marketplace", name="marketplace")
async def marketplace(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "marketplace.html",
        {
            "request": request,
            "user_id": user_email,
            "wallet": {"balance": 0.0, "credits": 0.0},
            "internal_currency": "CMS Credits (CMSC)",
            "exchanges": [],
            "wallets": [],
            "plugins": engine.list_plugins(),
            "purchases": [],
            "message": None,
            "exchange_info": None,
            "plugin_message": None,
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
    return result

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
