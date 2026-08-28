# CMS-my — ROUTES MAP (фактическое состояние 2026-08-27)

## Страницы (GET / api_route)
- `GET /`, `/home` → index.html
- `GET /login`, `POST /login`, `POST /login/dev-admin-bypass` → login.html
- `GET /register`, `POST /register` → register.html
- `GET|POST /forgot-password` → forgot_password.html
- `GET /logout`
- `GET|POST /dashboard`
- `GET|POST /settings`
- `GET|POST /marketplace`
- `GET|POST /bot-management`
- `GET /manual-trading` → manual_trading.html
- `GET|POST /strategies`
- `GET|POST /testing` → testing.html
- `GET|POST /demo`
- `GET|POST /wallet`
- `GET|POST /copy-trading`
- `GET|POST /arbitrage`
- `GET|POST /admin`
- `GET /install` (шаблон есть, маршрут НЕ смонтирован в main.py)
- Auth: `/auth/{provider}`, `/auth/{provider}/callback`, `/auth/telegram/callback`

## API (все под /api/*)
### Учётка/профиль
- `GET /api/profile`, `GET /api/settings`, `POST /api/user/connect-exchange`,
  `POST /api/user/connect-arbitrage-exchange`
### Стратегии
- `POST /api/strategies/create`, `GET /api/strategies`, `GET /api/strategies/user`,
  `GET /api/strategies/public`, `GET /api/strategies/performance`,
  `POST /api/strategies/purchase`, `POST /api/strategies/activate`,
  `POST /api/strategy/execute`
### Торговля
- `POST /api/trading/test`, `POST /api/trading/manual`, `GET /api/trading/history`,
  `GET /api/trading/status`
### Бот
- `GET /api/bot/memory`, `POST /api/bot/generate`, `GET /api/bot/generation-status`,
  `POST /api/bot/auto-generate`, `POST /api/bot/start`, `POST /api/bot/stop`,
  `GET /api/bot/status`, `POST /api/bot/backtest`, `POST /api/bot/simulate`,
  `GET /api/bot/brain`, `GET /api/bot/config`
### Рынок
- `GET /api/market/data`, `/api/market/history`, `/api/market/news`,
  `/api/market/signal`, `/api/market/trending`, `/api/market/listings`
### Риск
- `GET /api/risk/status`, `POST /api/risk/score`, `POST /api/risk/kill-switch`
### Демо
- `POST /api/demo/trade`, `GET /api/demo/status`, `POST /api/demo/toggle`,
  `GET /api/demo/balance`, `GET /api/demo/history`
### Кошелёк/биржи
- `GET /api/wallet/balance`, `POST /api/wallet/connect`, `GET /api/exchanges`
### Копи-трейдинг
- `POST /api/copy-trading/toggle`, `/api/copy-trading/settings`, `/api/copy-trading/reset`
### Арбитраж
- `POST /api/arbitrage/start`, `/api/arbitrage/stop`, `GET /api/arbitrage/status`,
  `POST /api/arbitrage/scan`
### Служебные
- `GET /api/chat`, `POST /api/feedback`, `GET /api/notifications`,
  `GET /api/admin/stats`, `GET /api/admin/settings`, `GET /api/report`, `GET /api/metrics`
### Health (admin router + health router)
- `/health`, `/health/live|ready|db|exchange|websocket|execution|version`
