# CMS-my — Full Connection / Logic Map

Baseline: `main` @ `1b7fdd643ffd01e3da9f3ebc6682859568c76215`

## System graph

```text
Browser
  │
  ├─ Jinja templates (`templates/*.html`)
  │    └─ forms / inline JS / static JS
  │
  ▼
FastAPI `backend.main:app`
  │
  ├─ session auth
  ├─ ad-hoc validation
  ├─ partial risk gates
  ├─ partial CSRF (admin live controls only)
  └─ partial rate limiting (helpers exist but are not wired)
  │
  ├───────────────┬─────────────────────┬─────────────────────┐
  ▼               ▼                     ▼                     ▼
CMSEngine     StrategyManager       RiskManager          Public CCXT/RSS
  │               │                     │                     │
  ├─ User         └─ DailyHarvester     ├─ kill switch       ├─ ticker
  ├─ Plugin           strategies        ├─ daily PnL          ├─ order book
  ├─ UserPlugin                          ├─ drawdown          ├─ OHLCV
  ├─ LearningMemory                      └─ position fraction └─ CoinDesk RSS
  ├─ Wallet
  ├─ Trade
  ├─ AuditLog
  ├─ BotStat
  └─ SiteSetting
  │
  ▼
SQLite: `cms_core.db` + market DB `cms_v12.db`

Separate real-order path:
ExchangeService → execution_gateway → security/execution_policy + LiveControlState → CCXT private executor

Separate Shadow path:
Admin API → AIShadowTrader → StrategyManager + RiskManager → virtual Trade → monitor/settle
                                      ▲
                                      │
                             AIShadowMarketFeed → public CCXT ticker
```

## Authentication flow

`GET /login` → login template → `POST /login` → `CMSEngine.secure_login` → session `user_email`/`is_admin` → protected page/API.

Social:
`/auth/google|github` → OAuth state in session → provider callback → token exchange → profile → create/find user → `_login_user`.

Telegram:
`/auth/telegram/callback` → HMAC validation with bot token → synthetic `telegram_<id>@telegram.local` identity → create/find user → session.

Gap: there is no actual `/install` HTTP flow on main even though installer components exist in the repository/history.

## Marketplace flow

`GET /marketplace`
→ authenticated session
→ `_strategy_performance()`
→ `refresh_history()` via public CCXT
→ `evaluate_strategies()`
→ `_strategy_catalog()`
→ `CMSEngine.user_plugins()`
→ template.

Plugin purchase:
`POST /marketplace action=buy_plugin`
→ `price_for_duration()`
→ `CMSEngine.purchase_plugin()`
→ UserPlugin access window
→ message to template.

**Broken business invariant:** wallet CMSC is not debited and no payment/ledger record is created.

Exchange connection from marketplace:
`POST /marketplace action=connect_exchange`
→ direct CCXT constructor
→ optional sandbox
→ `load_markets()`
→ `CMSEngine.update_wallet()` with masked key
→ audit log
→ message.

**Duplication:** this is separate from `ExchangeService.connect()`.

Wallet connection:
`POST /marketplace action=connect_wallet`
→ Wallet provider/address persisted → message.

Telegram:
`POST /marketplace action=connect_telegram`
→ only username persisted.

**UI mismatch:** token input exists but is ignored.

## Trading test flow

`POST /api/trading/test`
→ session auth
→ `RiskManager.decide(current_balance, 1.0)`
→ pair validation
→ `StrategyManager.execute(news_sentiment, price_change, balance)`
→ `HFTBot.simulate()`
→ `CMSEngine.record_memory('strategy_test', ...)`
→ `CMSEngine.record_trade(... mode='test' ...)`
→ `RiskManager.record()`
→ JSON.

Important: risk decision uses hard-coded leverage `1.0` instead of configured strategy leverage. This means the pre-trade risk check can approve a request using different leverage from the actual StrategyManager execution. **Additional HIGH logic defect.**

## Manual trade flow

`POST /api/trading/manual`
→ session auth
→ pair/side/number validation
→ fee calculation from strategy config
→ `Trade(mode='manual')`
→ audit
→ `{status:'executed'}`.

No ExchangeService/private order call occurs.

**Required semantic decision:** either rename to paper/manual simulation or route through an explicitly guarded live gateway; do not silently change behavior.

## Strategy execution flow

`POST /api/strategy/execute`
→ session auth
→ RiskManager using configured leverage
→ StrategyManager
→ RiskManager.record
→ audit/stat
→ JSON.

This is virtual/domain execution only; it does not call an exchange.

## Market data flow

`GET /api/market/data`
→ auth
→ public exchange validation
→ CCXT ticker + order book
→ `refresh_candles()`
→ `cms_v12.db`
→ JSON.

`GET /api/market/history`
→ auth
→ timeframe validation
→ CCXT OHLCV
→ `store_intraday_candles()` / `refresh_history()`
→ market SQLite
→ JSON.

`GET /api/market/news`
→ auth
→ optional CoinDesk RSS fetch
→ `store_news()` filters future-dated items
→ keyword sentiment
→ JSON.

`GET /api/market/signal`
→ auth
→ `_market_signal()`
→ public candles/history
→ StrategyManager
→ signal JSON.

## Bot/HFT flow

`POST /api/bot/start`
→ admin auth
→ RiskManager kill switch
→ HFTBot.start()
→ audit/stat.

`POST /api/bot/stop`
→ admin auth
→ HFTBot.stop()
→ audit/stat.

`POST /api/bot/backtest`
→ auth
→ public daily OHLCV
→ evaluate all plugin names
→ results JSON.

**Reporting defect:** results use `monthly_return_pct` for a backtest based on up to 365 days.

`POST /api/bot/simulate`
→ no auth
→ CMSProductionHFTBot.trade_loop()
→ process-local capital/brain/history
→ metrics JSON.

**Security/test defect:** anonymous access is currently possible while tests expect 401.

## Real exchange flow

`ExchangeService.connect()`
→ validates user id and credentials
→ supported exchange
→ CCXT authenticated client
→ sandbox optional
→ `load_markets()`
→ `fetch_balance()`
→ client stored in process memory.

`ExchangeService.create_order()`
→ connection lookup
→ symbol/type/side/amount validation
→ minimum amount validation
→ `submit_real_order()`
→ `assert_real_execution_allowed()`
→ `assert_live_controlled()`
→ actual `client.create_order()`.

`ExchangeService.cancel_order()` follows the same gateway.

**Important:** current `main.py` has no route wired to `ExchangeService.create_order()` or `cancel_order()`. The real-order architecture therefore exists but is not connected to the main UI trading flow.

## Live-control flow

`POST /api/admin/live-controls/global`
→ admin session
→ CSRF
→ `LIVE_CONTROL_STATE.set_global_kill_switch()`.

`POST /api/admin/live-controls/bots/{bot_id}`
→ admin + CSRF
→ bot LIVE flag.

`POST /api/admin/live-controls/ai-bots/{ai_bot_id}`
→ admin + CSRF
→ AI-bot LIVE flag.

These controls are process-local and disappear on restart; startup is fail-closed.

## Shadow flow

`POST /api/admin/ai-shadow/evaluate`
→ admin
→ `require_shadow_mode()` rejects only LIVE mode
→ `AIShadowTrader.evaluate()`
→ StrategyManager
→ RiskManager
→ AI confidence threshold
→ virtual Trade open
→ memory/audit/stat.

`POST /api/admin/ai-shadow/monitor`
→ public market price supplied by caller
→ find open Trade
→ SL/TP hit detection
→ `settle()`.

`POST /api/admin/ai-shadow/feed/start`
→ admin + non-LIVE mode
→ public CCXT ticker loop
→ `monitor()`.

No private order calls are made by Shadow.

## Response/output contracts

- HTML page routes return Jinja TemplateResponse or RedirectResponse.
- JSON API routes return dictionaries/lists or FastAPI HTTPException errors.
- Browser JS generally expects `data.detail` for failures.
- Several backend handlers expose raw exception strings, so the stable safe-error contract is not enforced.
- Template endpoint names are supplied through a custom `templates.env.globals['url_for']` wrapper.

## Static asset contract

`main.py` mounts `BASE_DIR/frontend` at `/static`.
`templates/base.html` references:
- `/static/style.css`
- `/static/market_terminal.css`
- `/static/market_live.css`
- `/static/market_terminal.js`
- `/static/market_live.js`
- `/static/market_terminal_patch.js`

Therefore the `frontend/` copies are authoritative for the Jinja app. Root `static/` is a duplicate tree and must not be edited assuming it affects the current UI.

## Deployment flow

### Codespace
`.devcontainer/devcontainer.json`
→ Python 3.12 image
→ install requirements
→ `scripts/codespace-start.sh`
→ `run.py`
→ `uvicorn backend.main:app` on 8000.

### Netlify
`netlify.toml`
→ all traffic redirected to `/.netlify/functions/api/:splat`
→ `netlify/functions/api.py`
→ cwd `/tmp`
→ `/tmp` market/config paths
→ Mangum adapter
→ FastAPI app.

### Docker/PaaS
Dockerfile runs `backend.main:app` on `$PORT` and exposes 8000. Render/Railway/Fly health checks expect `/health`, which is currently not mounted.

### Vercel
`vercel.json` maps `backend/main.py` to `@vercel/python` and routes all requests there. Current main also contains a custom Vercel build command.

## End-to-end verification matrix

A function is not DONE until all are checked:
`UI/template → JS/form → endpoint → auth/CSRF/rate/risk → service → DB/external → response → UI state → test → deployment runtime`.
