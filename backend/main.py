from pathlib import Path
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
app.add_middleware(SessionMiddleware, secret_key="super_secret_key_v12")
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.include_router(admin_router)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
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

@app.get("/")
async def serve_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "user_id": request.session.get("user_email")})

@app.get("/login")
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

@app.get("/register")
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

@app.get("/forgot-password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "message": None, "user_id": request.session.get("user_email")})

@app.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...)):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "Инструкции по восстановлению пароля отправлены на указанный email.", "user_id": request.session.get("user_email")})

@app.get("/dashboard")
async def dashboard(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    user = engine.get_user(user_email)
    username = user.email if user else user_email
    balance = "—"
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username, "email": user_email, "balance": balance, "user_id": user_email})

@app.get("/logout")
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
        with open("ADVANCED_TEST_REPORT.md", "r", encoding="utf-8") as report_file:
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
