# CMS-my — Complete Function / Route / Logic Map

Date: 2026-08-21
Baseline: `main` audit baseline `1b7fdd643ffd01e3da9f3ebc6682859568c76215`.

## Universal function contract

Every production function is considered complete only when this chain is proven:

`UI/template → event/form → route → authentication → CSRF → rate limit → mode/risk gate → controller → domain/service → persistence/external I/O → response/error contract → UI state → regression test → real HTTP smoke → deployment runtime`.

## Application modules

### Entry/application layer
- `backend/main.py` — FastAPI application, sessions, static mount, page routes, API routes, OAuth/Telegram, marketplace, trading, market data and bot orchestration.
- `backend/admin.py` — `/api/admin/*` administrative and AI Shadow routes.
- `netlify/functions/api.py` — Mangum adapter; changes cwd/storage targets for serverless execution.
- `run.py` / deployment manifests — process startup contracts.

### Domain/persistence
- `backend/cms_core.py` — User, Plugin, UserPlugin, LearningMemory, BotStat, AuditLog, Wallet, Trade, SiteSetting and CRUD/business transitions.
- `backend/market_history.py` — market/news SQLite storage and CCXT/RSS refresh pipeline.
- `backend/strategy_performance.py` — strategy evaluation and license pricing.
- `backend/modules/daily_harvester.py` — compound-harvesting calculation module.
- `backend/modules/strategy_manager.py` — strategy selection, validation, execution calculations and configuration.
- `backend/risk_management.py` — risk decisions, daily loss/drawdown/stop-loss state.

### Trading/AI
- `backend/bot.py` — HFTBot simulation/status/start-stop state.
- `backend/hft_brain.py` — CMSProductionHFTBot and AI memory/trade-loop behavior.
- `backend/ai_shadow.py` — paper/shadow evaluate/monitor/settle lifecycle.
- `backend/ai_shadow_feed.py` — public-market feed driving Shadow monitoring.
- `backend/exchange_service.py` — authenticated CCXT client registry and guarded real order/cancel operations.

### Security
- `backend/security/execution_policy.py` — DEMO/BACKTEST/SHADOW/LIVE policy and environment gate.
- `backend/security/execution_gateway.py` — intended single choke point before private order/cancel.
- `backend/security/live_controls.py` — process-local global/bot/AI LIVE controls, fail-closed by default.
- `backend/security/request_policy.py` — authentication/mode/rate-limit helper policy.
- `backend/security/http_protection.py` — CSRF/HTTP protection helpers.
- `backend/security/credential_safety.py` — credential masking/safety utilities.
- `backend/security/safe_errors.py` — stable client-safe error helper.
- `backend/execution_guard.py`, `backend/ccxt_guard.py`, `backend/live_guard.py`, `backend/live_trading_guard.py` — overlapping legacy/security guard surfaces requiring reference tracing before any deletion.

## Route map — page/UI layer

| Route | Handler purpose | Primary state | Output |
|---|---|---|---|
| `GET /` | Landing/root | session | `templates/index.html` |
| `GET /home` | Home | session | HTML |
| `GET/POST /login` | credential login | session/User | HTML/redirect |
| `POST /login/dev-admin-bypass` | development admin login | session | redirect |
| `GET/POST /register` | account creation | User/session | HTML/redirect |
| `GET/POST /forgot-password` | password recovery UI | none | HTML/message |
| `GET/POST /dashboard` | dashboard | wallet/memory/settings | HTML |
| `GET/POST /settings` | user settings | session/User | HTML |
| `GET/POST /marketplace` | strategy/plugin/exchange/wallet/Telegram actions | Wallet/UserPlugin/SiteSetting | HTML |
| `GET/POST /bot-management` | bot configuration/control | HFTBot/StrategyManager | HTML |
| `GET/POST /wallet` | CMSC/payment UI | Wallet/settings | HTML |
| `GET/POST /admin` | admin UI | users/plugins/wallet/site/risk | HTML |

## API map — identity and session

- `GET /auth/{provider}` → provider config → session OAuth state → redirect.
- `GET /auth/{provider}/callback` → validate state → token exchange → provider profile → create/find User → session.
- `GET /auth/telegram/callback` → Telegram HMAC verification → synthetic identity → User → session.
- `POST /login` → `CMSEngine.secure_login` → session.
- `POST /register` → `CMSEngine.create_user` → session.
- `GET /logout` → clear session.

## API map — marketplace/wallet

- `POST /marketplace buy_plugin` → license price → `CMSEngine.purchase_plugin` → UserPlugin. **Accounting gap: no CMSC debit/payment ledger.**
- `POST /marketplace connect_exchange` → direct CCXT → `load_markets()` → masked wallet metadata. **Bypasses ExchangeService/security architecture.**
- `POST /marketplace connect_wallet` → Wallet provider/address persistence.
- `POST /marketplace connect_telegram` → username persistence; token field currently ignored.
- `POST /api/strategies/activate` → authenticated user → plugin/access → performance lookup → UserPlugin activation → in-memory strategy config. **Persistence/executable-strategy contract incomplete.**

## API map — trading

- `POST /api/trading/test` → auth → `RiskManager.decide()` → `StrategyManager.execute()` → `HFTBot.simulate()` → LearningMemory → Trade(mode=test) → RiskManager.record → JSON.
  - Defect: risk gate uses hard-coded leverage `1.0`, while StrategyManager can use configured leverage.
- `POST /api/trading/manual` → auth → input/fee validation → local Trade/audit → JSON `{status: executed}`. **No private exchange order occurs.**
- `GET /api/trading/history` → auth → Trade list.
- `POST /api/strategy/execute` → auth → RiskManager → StrategyManager → risk/stat/audit → JSON. Virtual/domain execution; no exchange call.
- `GET /api/strategies` → auth → performance → catalog JSON.

## API map — market data

- `GET /api/market/data` → auth → public CCXT ticker/order book → candle refresh → market DB → JSON.
- `GET /api/market/history` → auth → timeframe validation → public CCXT OHLCV → market DB → JSON.
- `GET /api/market/news` → auth → RSS → market DB → keyword sentiment → JSON.
- `GET /api/market/signal` → auth → public candles/history → StrategyManager → signal JSON.

## API map — bot/HFT

- `GET /api/trading/status` → auth → HFTBot.status.
- `POST /api/bot/start` → admin → RiskManager kill switch → HFTBot.start → audit/stat.
- `POST /api/bot/stop` → admin → HFTBot.stop → audit/stat.
- `GET /api/bot/status` → auth → HFTBot.status.
- `POST /api/bot/backtest` → auth → public OHLCV → strategy evaluation → JSON.
- `POST /api/bot/simulate` → currently no auth → CMSProductionHFTBot.trade_loop → process-local state → JSON. **Security/test mismatch.**
- `GET /api/bot/brain` → admin → process-local AI memory summary.
- `GET /api/metrics` → admin → bot/brain/strategy/risk metrics.

## API map — risk

- `GET /api/risk/status` → auth → RiskManager.status.
- `POST /api/risk/kill-switch` → admin → RiskManager.kill_switch only.

## API map — exchange

- `POST /api/user/connect-exchange` → currently unauthenticated → direct CCXT → `load_markets()` → audit/stat. **Duplicate/unsafe path.**
- `ExchangeService.connect()` → authenticated credentials → CCXT client → load markets → balance → process-local registry.
- `ExchangeService.create_order()` → validation → `execution_gateway.submit_real_order()` → environment LIVE gate → LiveControlState → private `client.create_order()`.
- `ExchangeService.cancel_order()` → same guarded gateway path.
- Main UI currently has no normal route that exposes `ExchangeService.create_order/cancel_order`.

## Admin router map

- `GET/POST /api/admin/live-controls/*` — admin + CSRF → global/bot/AI LIVE controls.
- `GET /api/admin/live-controls/audit` — admin → process-local control audit.
- User/plugin administration — admin → CMSEngine.
- AI Shadow evaluate/settle/monitor/feed start/feed stop/feed status — admin + non-LIVE mode → AI Shadow domain.

## Function-level logic branches

### StrategyManager
`load_config → validate strategy/leverage/risk/fee → choose strategy branch → DailyCompoundHarvester calculation → fee deduction → net balance/PnL → response`.
Implemented named branches observed: `pure_harvester`, `high_frequency_momentum`, `compound_defender`. Unknown names fall back to the base/pure processing path; this must never be mistaken for successful execution of an unknown plugin strategy.

### RiskManager
`decide(balance, leverage, stop_loss_pct) → kill switch → numeric validation → daily loss → drawdown → stop-loss → position fraction`.
`record(pnl,balance)` updates process-local daily PnL/peak.

### ExchangeService
`connect → validate credentials/exchange → CCXT client → optional sandbox → load_markets → fetch_balance → in-memory client`.
`create_order/cancel_order → validation → execution_gateway → execution_policy + live controls → private executor`.

### AI Shadow
`evaluate → non-LIVE gate → strategy → risk → AI confidence threshold → virtual Trade open → memory/audit/stat`.
`monitor → open virtual trades → market price → SL/TP → settle`.
`feed.start → non-LIVE → public CCXT ticker → monitor/settle only`.

### Persistence
Core DB: `cms_core.db` via CMSEngine.
Market DB: `cms_v12.db` via market_history.
Netlify function deliberately redirects writable SQLite/config state to `/tmp`.

## Response contracts

- HTML: Jinja `TemplateResponse` or `RedirectResponse`.
- JSON: dict/list or HTTPException.
- Frontend generally expects `data.detail` on failure.
- Safe error helper exists but raw provider/exception text is still exposed by several handlers.
- Template `url_for` is custom-wrapped because static references use `filename → path` translation.

## Active template/static contract

`backend/main.py` mounts `frontend/` at `/static`; therefore `frontend/` is authoritative for active static assets. Root `static/` is duplicate/legacy until proven otherwise.
`templates/*.html` are the active Jinja page templates. `frontend/index.html` is a separate legacy/application surface and directly calls the duplicate exchange endpoint.
