# CMS-my — API MAP (фактические эндпоинты 2026-08-27)

## Принципы
- Все /api/* требуют авторизацию (кроме /api/bot/simulate — ДЕФЕКТ C-02)
- Ответы JSON: `{ok:true,data...,request_id}` или `{ok:false,code,detail,request_id}`
- CSRF: только admin live-controls имеют проверку — ДЕФЕКТ C-04
- Rate limit: request_policy.py есть, но НЕ подключен — ДЕФЕКТ H-02

## Группы API

### User/Profile
- `GET /api/profile` — профиль пользователя (email, role, username)
- `GET /api/settings` — настройки
- `POST /api/user/connect-exchange` — подключить биржу (legacy path, дублирует ExchangeService)
- `POST /api/user/connect-arbitrage-exchange` — второй API для арбитража

### Strategy
- `POST /api/strategies/create` — создать StrategyTemplate
- `GET /api/strategies` — каталог стратегий (маркетплейс)
- `GET /api/strategies/user` — стратегии пользователя
- `GET /api/strategies/public` — публичные стратегии
- `GET /api/strategies/performance` — performance стратегий
- `POST /api/strategies/purchase` — покупка плагина (НЕ списывает CMSC — ДЕФЕКТ H-04)
- `POST /api/strategies/activate` — активация (НЕ сохраняется persistent — ДЕФЕКТ H-06)
- `POST /api/strategy/execute` — исполнение стратегии (virtual)

### Trading
- `POST /api/trading/test` — тестовый прогон (hardcoded leverage 1.0 — дефект)
- `POST /api/trading/manual` — ручная торговля (ВОЗВРАЩАЕТ "executed" БЕЗ РЕАЛЬНОГО ОРДЕРА — C-06)
- `GET /api/trading/history` — история сделок
- `GET /api/trading/status` — статус бота/торговли

### Bot
- `GET /api/bot/memory` — память обучения
- `POST /api/bot/generate` — генерация стратегий
- `GET /api/bot/generation-status` — статус генерации
- `POST /api/bot/auto-generate` — автогенерация
- `POST /api/bot/start` — запуск бота (только админ, process-local, no background worker — H-09)
- `POST /api/bot/stop` — остановка
- `GET /api/bot/status` — статус
- `POST /api/bot/backtest` — бэктест (monthly_return_pct named as roi — дефект)
- `POST /api/bot/simulate` — симуляция (ANONYMOUS — C-02)
- `GET /api/bot/brain` — AI brain (только админ)
- `GET /api/bot/config` — конфиг бота
- `GET /api/metrics` — метрики

### Market Data
- `GET /api/market/data` — тикер
- `GET /api/market/history` — OHLCV
- `GET /api/market/news` — новости RSS
- `GET /api/market/signal` — торговый сигнал
- `GET /api/market/trending` — трендовые пары
- `GET /api/market/listings` — листинги маркетплейса

### Risk
- `GET /api/risk/status` — текущий risk score
- `POST /api/risk/score` — расчёт risk score
- `POST /api/risk/kill-switch` — kill switch

### Demo
- `POST /api/demo/trade` — демо-сделка
- `GET /api/demo/status` — статус демо
- `POST /api/demo/toggle` — включить/выключить демо
- `GET /api/demo/balance` — демо-баланс
- `GET /api/demo/history` — демо-история

### Wallet/Exchanges
- `GET /api/wallet/balance` — баланс кошелька
- `POST /api/wallet/connect` — подключить кошелёк
- `GET /api/exchanges` — список подключенных бирж

### Copy Trading
- `POST /api/copy-trading/toggle`
- `POST /api/copy-trading/settings`
- `POST /api/copy-trading/reset`

### Arbitrage
- `POST /api/arbitrage/start`
- `POST /api/arbitrage/stop`
- `GET /api/arbitrage/status`
- `POST /api/arbitrage/scan`

### Admin
- `GET /api/admin/stats`
- `GET /api/admin/settings`
- `GET /api/admin/live-controls/*`

### Health
- `/health`, `/health/live`, `/health/ready`, `/health/db`, `/health/exchange`, `/health/websocket`, `/health/execution`, `/health/version`
