# Анализ: Спека vs Текущее состояние — 27.08.2026

## ✅ УЖЕ СДЕЛАНО (подтверждено и работает)

### Core CMS
- [x] FastAPI app, Jinja2, session auth, redirects
- [x] Login/Register/Forgot Password
- [x] Dev admin bypass
- [x] Google/GitHub OAuth routes
- [x] Telegram callback
- [x] Password migration (SHA-256 → scrypt)
- [x] Logout
- [x] `/health` endpoint (200)

### Database Models (всё в cms_core.py)
- [x] User, Plugin, UserPlugin, LearningMemory, BotStat
- [x] AuditLog, Wallet, Trade, SiteSetting, DemoSession
- [x] StrategyTemplate
- [x] Все CRUD операции

### Bot Core (НЕ ТРОНУТ — работает как задумано)
- [x] HFTBot (start/stop/status/simulate/execute_trade/memory)
- [x] CMSProductionHFTBot + AICryptoMemoryBrain
- [x] 10 стратегий (daily_harvester.py)
- [x] StrategyGenerator (auto-generate, backtest, publish)
- [x] StrategyManager (load, config, execute)
- [x] RiskManager (decide, record, kill-switch)
- [x] TradingExecutionGate

### Trading Features
- [x] Demo trade API (`/api/demo/trade`)
- [x] Manual trade API (`/api/trading/manual`)
- [x] Strategy test (`/api/trading/test`)
- [x] Strategy execute (`/api/strategy/execute`)
- [x] Backtest (`/api/bot/backtest`)
- [x] Bot generate strategies (`/api/bot/generate`)
- [x] Market data/history/news/signal APIs

### AI Shadow Trading
- [x] AIShadowTrader (evaluate/monitor/settle)
- [x] AIShadowMarketFeed (start/stop/status)
- [x] Admin API для shadow

### Security Modules (существуют, НЕ подключены к main.py)
- [x] execution_gateway.py
- [x] execution_policy.py
- [x] live_controls.py
- [x] request_policy.py
- [x] credential_safety.py
- [x] http_protection.py
- [x] safe_errors.py

### UI (Pionex-style)
- [x] Новый CSS дизайн (dark/light/auto)
- [x] base.html с sidebar навигацией
- [x] Dashboard, Bot Management, Manual Trading
- [x] Marketplace (platinum/premium)
- [x] Strategies, Testing, Demo
- [x] Wallet, Settings, Admin
- [x] Copy Trading (НОВОЕ)
- [x] Login, Register, Forgot Password

### Static Assets
- [x] style.css (новый Pionex-style)
- [x] terminal.css (торговый терминал)
- [x] market_terminal.css, market_live.css
- [x] market_terminal.js, market_live.js, trading_chart.js

---

## ❌ НЕ СДЕЛАНО / ПОТЕРЯНО (по спеке)

### CRITICAL — Не подключены к main.py
1. **health.py / health_endpoint.py** — health router НЕ registered в app
2. **exchange_service.py** — единый exchange adapter НЕ используется (marketplace использует прямой CCXT)
3. **execution_gateway.py** — единая точка исполнения ордеров НЕ подключена
4. **execution_policy.py** — центральная политика исполнения НЕ подключена
5. **live_controls.py** — LIVE контроль НЕ интегрирован
6. **request_policy.py** — rate limiting НЕ подключён
7. **ccxt_guard.py** — guard для CCXT НЕ активен
8. **http_protection.py** — HTTP security helpers НЕ подключены
9. **safe_errors.py** — защита ошибок НЕ активна

### CRITICAL — Не работают как надо
10. **Покупка плагина** — НЕ списает CMSC, нет payment ledger
11. **Активация стратегии** — НЕ сохраняется через save_strategy_config
12. **Exchange connection** — два отдельных пути (marketplace + api/user/connect-exchange)
13. **Telegram token** — собирается UI, но не проверяется
14. **Bot lifecycle** — start/stop НЕ создаёт реальный фоновый цикл
15. **Process-local state** — bot/brain memory не переживает рестарт

### CRITICAL — CSRF и безопасность
16. **CSRF middleware** — НЕ установлен глобально (только в admin live-controls)
17. **Анонимный /api/bot/simulate** — должен требовать авторизацию
18. **Анонимный /api/user/connect-exchange** — должен требовать авторизацию
19. **Два kill-switch** — RiskManager + LiveControlState не объединены

### HIGH — Отсутствуют API/UI
20. **POST /api/trading/manual** — говорит "executed", но не отправляет ордер
21. **CMSC payment ledger** — нет записи платежей
22. **Background bot loop** — нет реального цикла торговли
23. **Unified kill switch** — два независимых стопа

### MEDIUM — Дизайн/UX
24. **admin.html** — НЕ обновлён под Pionex-style
25. **bot_management.html** — НЕ обновлён под Pionex-style
26. **manual_trading.html** — НЕ обновлён под Pionex-style
27. **marketplace.html** — НЕ обновлён под Pionex-style
28. **demo.html** — НЕ обновлён под Pionex-style
29. **strategies.html** — НЕ обновлён под Pionex-style
30. **install.html** — есть но НЕ mounted

### MEDIUM — Тесты
31. **tests/** — 25 тестов существуют, НЕ запускаются
32. **HTTP smoke tests** — нет
33. **UI verification** — нет

### LOW — Отсутствует
34. **HTTP installer /install** — компоненты есть, но route НЕ mounted
35. **Production first-admin flow** — нет
36. **Rate limiting** — request_policy.py есть, НЕ подключён
37. **CI/CD** — workflows есть, но false-positive

---

## 📋 ПРИОРИТЕТ ВОССТАНОВЛЕНИЯ

### Phase 1 — CRITICAL (подключить модули к main.py)
1. Подключить health router
2. Подключить exchange_service (единый путь)
3. Подключить execution_gateway + execution_policy
4. Подключить live_controls + request_policy
5. Подключить ccxt_guard + safe_errors
6. Исправить покупку плагина (CMSC debit + ledger)
7. Исправить активацию стратегии (persistent)
8. Объединить kill-switch

### Phase 2 — CRITICAL (безопасность)
9. Добавить CSRF middleware
10. Защитить анонимные API endpoints
11. Объединить exchange connection paths

### Phase 3 — HIGH (функционал)
12. Background bot lifecycle ( реальный цикл )
13. Manual trade → execution gateway
14. Persistent bot/brain state (SQLite)
15. Telegram token validation

### Phase 4 — MEDIUM (UI)
16. Обновить admin.html → Pionex-style
17. Обновить bot_management.html → Pionex-style
18. Обновить manual_trading.html → Pionex-style
19. Обновить marketplace.html → Pionex-style
20. Обновить demo.html → Pionex-style
21. Обновить strategies.html → Pionex-style

### Phase 5 — TEST
22. Запустить pytest suite
23. HTTP smoke tests
24. UI verification
