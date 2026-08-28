# Недостающие API эндпоинты — 26.08.2026

JS на страницах вызывает эндпоинты, которых нет в `backend/main.py`.
Нужно добавить заглушки или полную реализацию.

## Приоритет 1 — Критичные (вызываются на основных страницах)
```python
# GET /api/wallet/balance — вызывается на странице Кошелька
@app.get("/api/wallet/balance")
async def api_wallet_balance(request: Request):
    user = _require_user(request)
    wallet = engine.get_or_create_wallet(user["email"])
    return {"balance": wallet.get("balance", 0), "currency": "EUR"}

# GET /api/settings — вызывается в настройках
@app.get("/api/settings")
async def api_get_settings(request: Request):
    user = _require_user(request)
    return {"theme": user.get("theme", "light"), "email": user["email"]}

# GET /api/profile — вызывается в профиле
@app.get("/api/profile")
async def api_profile(request: Request):
    user = _require_user(request)
    return {"username": user.get("username"), "email": user["email"]}
```

## Приоритет 2 — Функциональные
```python
# GET /api/exchanges — список бирж
@app.get("/api/exchanges")
async def api_exchanges():
    return {"exchanges": list(SUPPORTED_MARKET_EXCHANGES)}

# GET /api/market/trending — тренды маркета
@app.get("/api/market/trending")
async def api_market_trending():
    return {"trending": []}

# GET /api/demo/balance — баланс демо
@app.get("/api/demo/balance")
async def api_demo_balance(request: Request):
    user = _require_user(request)
    return {"balance": 100.0, "currency": "EUR"}

# GET /api/demo/history — история демо сделок
@app.get("/api/demo/history")
async def api_demo_history(request: Request):
    user = _require_user(request)
    return {"trades": []}

# GET /api/bot/config — конфигурация бота
@app.get("/api/bot/config")
async def api_bot_config(request: Request):
    return {"strategy": bot.current_strategy or "pure_harvester", "active": bot.active}
```

## Приоритет 3 — Утилитарные
```python
# GET /api/notifications
@app.get("/api/notifications")
async def api_notifications(request: Request):
    return {"notifications": []}

# GET /api/admin/stats
@app.get("/api/admin/stats")
async def api_admin_stats(request: Request):
    _require_admin(request)
    return {"users": 0, "strategies": 0}

# GET /api/admin/settings
@app.get("/api/admin/settings")
async def api_admin_settings(request: Request):
    _require_admin(request)
    return {}
```

## Важно
Все эндпоинты должны проверять авторизацию через `_require_user(request)`.
Иначе они вернут 302 redirect на `/login` (что и вызывает "file not found" в AJAX-запросах).
