# CMS-my — Full Functionality Inventory / Recovery Map

Date: 2026-08-27
Source baseline: current `main`; cross-reference with `CMS_WORK/BRANCH_MAP_2026-08-21.md`, `FUNCTION_MAP_2026-08-21.md`, `CONNECTION_MAP_2026-08-21.md`, `STRICT_AUDIT_2026-08-21.md`, `PROJECT_STATUS.md`.

## Purpose
This is an inventory, not a claim that every item is currently reachable from the UI. Items are separated into: confirmed in current source, backend-only/not currently exposed, legacy/duplicate, and historical recovery candidates. Nothing is to be deleted merely because it is not displayed.

## 1. Core application
- FastAPI application in `backend/main.py`.
- Jinja2 page rendering and redirects.
- Session authentication and role state (`user_email`, `is_admin`).
- Custom template `url_for` compatibility wrapper.
- Static asset mount from `frontend/`.
- Admin router mounted from `backend/admin.py`.
- OAuth Google/GitHub login flow with state validation.
- Telegram login callback with HMAC verification.
- Password authentication and legacy SHA-256 → scrypt migration.
- Registration, logout and password-recovery UI surfaces.

## 2. User / CMS data model and persistence
`backend/cms_core.py` confirms these domain models:
- User: email, password hash, KYC status, role.
- Plugin: name, price, description.
- UserPlugin: purchased/active plugin access and access expiration.
- LearningMemory: action/result/context history.
- BotStat: bot/system metrics.
- AuditLog: security/business audit records.
- Wallet: CMSC/credits balance, wallet provider/address, exchange provider/masked key, sandbox flag, Telegram username.
- Trade: pair, mode, strategy, PnL, balance and timestamp.
- SiteSetting: key/value configuration.

Core operations include user creation/authentication, plugin CRUD, default strategy plugin creation, plugin purchase/access extension, activation, memory/trade/audit/stat persistence, wallet updates and site settings.

## 3. Marketplace / plugins
Visible/application surface:
- Strategy/plugin catalog.
- Plugin purchase and access duration choices.
- Plugin activation.
- Exchange connection UI.
- Wallet connection UI.
- Telegram connection UI.
- Strategy performance/catalog information.

Confirmed named default strategy plugins:
1. `pure_harvester`
2. `high_frequency_momentum`
3. `compound_defender`

Important current gaps:
- Plugin purchase creates/extends `UserPlugin` access but does not debit Wallet CMSC or create a payment ledger.
- Activation writes strategy state in memory and is not persisted through `save_strategy_config()`.
- Unknown plugin/strategy names can be marked active while execution falls back to the base/pure path.
- Marketplace exchange connection is a duplicate direct-CCXT path instead of the central ExchangeService.
- Telegram token is collected by UI but ignored by the current marketplace handler; username is persisted.

## 4. Dashboard
Intended/current page surface:
- Dashboard page.
- Wallet/balance information.
- Learning memory / user state.
- Settings/site state used by dashboard.

Status: route exists; complete UI-to-backend verification remains TODO in PROJECT_STATUS.

## 5. Wallet / CMSC / payments
Confirmed domain capability:
- Wallet model with `credits`.
- Wallet provider/address persistence.
- Exchange provider and masked key persistence.
- Sandbox flag.
- CMSC/credits balance is displayed/used in marketplace flows.

Current confirmed limitation:
- No complete CMSC payment/ledger accounting path is confirmed in current audit. Plugin purchase does not debit credits.
- Do not infer a complete payment gateway from the presence of payment UI/constants alone.

## 6. Market data terminal
Confirmed backend capabilities:
- Public CCXT exchange validation.
- Ticker.
- Order book.
- OHLCV/history.
- Candle refresh and SQLite market history storage.
- News/RSS ingestion.
- Keyword-based sentiment scoring.
- Market signal generation through StrategyManager.
- Frontend exchange-style candle canvas.
- OHLC, volume, grid, price scale and hover tooltip.
- Resize/DPR adaptation.
- Periodic history refresh.
- Binance WebSocket trade aggregation into 1-second OHLCV in live mode.
- Ticker fallback for other exchanges in 1-second live mode.

Important UI/backend contract:
`/api/market/history` returns objects `{timestamp, open, high, low, close, volume}`; frontend candle renderer was adapted to that object format.

## 7. Trading / strategy execution
### StrategyManager
Capabilities:
- Load strategy configuration.
- Validate strategy/leverage/risk/fee.
- Select strategy branch.
- DailyCompoundHarvester calculation.
- Fee deduction.
- Net balance/PnL calculation.
- Configuration save function exists.

Implemented strategy branches observed in audit:
- `pure_harvester` — base/compound-harvesting path.
- `high_frequency_momentum` — momentum/test path.
- `compound_defender` — defensive compound path.

Unknown strategy names currently fall back to the base/pure processing path; this is a defect, not an additional strategy.

### RiskManager
Capabilities:
- Kill switch state.
- Daily PnL tracking.
- Peak/drawdown tracking.
- Stop-loss checks.
- Position-fraction decision.
- Numeric validation.
- Record/update risk state.

Known defect:
`/api/trading/test` passes hard-coded leverage `1.0` to RiskManager while StrategyManager may use configured leverage.

### Trading routes
- `/api/trading/test`: authenticated virtual/test execution → risk → strategy → HFT simulation → memory/trade record → risk record → JSON.
- `/api/strategy/execute`: authenticated virtual/domain strategy execution → risk/stat/audit → JSON.
- `/api/trading/manual`: validates/calculates/records a local trade but currently returns `executed` without a private exchange order.
- `/api/trading/history`: authenticated trade history.
- `/api/strategies`: authenticated strategy catalog/performance.
- `/api/strategies/activate`: authenticated strategy/plugin activation.

## 8. Bot / HFT functionality
### `backend/bot.py` — HFTBot
- Simulation.
- Status.
- Start/stop state.
- Stats/event state.

Known limitation: start/stop toggles process-local state and does not itself launch/terminate a background trading loop.

### `backend/hft_brain.py` — CMSProductionHFTBot
- Production-oriented HFT brain/trade-loop behavior.
- AI memory/trade-loop state.
- Used by simulation endpoint and related metrics.

### Bot routes
- `/api/trading/status`.
- `/api/bot/start`.
- `/api/bot/stop`.
- `/api/bot/status`.
- `/api/bot/backtest`.
- `/api/bot/simulate`.
- `/api/bot/brain`.
- `/api/metrics`.

Known limitation: `/api/bot/simulate` is currently unauthenticated in the audited code and is therefore a security/test mismatch.

Known reporting issue: backtest uses up to 365 daily candles but exposes a field named `monthly_return_pct` as `roi`.

## 9. AI Shadow / paper trading
Modules:
- `backend/ai_shadow.py`.
- `backend/ai_shadow_feed.py`.

Capabilities:
- Shadow evaluate.
- Non-LIVE mode gate.
- Strategy + risk evaluation.
- AI confidence threshold.
- Virtual Trade opening.
- Memory/audit/stat recording.
- Monitoring open virtual trades.
- SL/TP detection.
- Settlement.
- Public CCXT feed start/stop/status.

No private exchange order is made by Shadow.

Admin endpoints cover evaluate, settle, monitor, feed start, feed stop and feed status.

## 10. Real exchange / live trading architecture
`backend/exchange_service.py`:
- Authenticated CCXT client registry.
- Exchange credential validation.
- Supported exchange validation.
- Optional sandbox.
- `load_markets()`.
- `fetch_balance()`.
- Real order creation.
- Order cancellation.

Security path:
`ExchangeService.create_order/cancel_order → execution_gateway → execution_policy → LiveControlState → private CCXT executor`.

Important: current main UI does not expose a normal route wired to `ExchangeService.create_order/cancel_order`; the architecture exists but the user-facing live execution path is incomplete.

## 11. Security modules / hidden functionality
Confirmed modules:
- `backend/security/execution_policy.py` — DEMO/BACKTEST/SHADOW/LIVE policy and environment gate.
- `backend/security/execution_gateway.py` — intended single choke point for private order/cancel.
- `backend/security/live_controls.py` — global/bot/AI LIVE controls, fail-closed by default.
- `backend/security/request_policy.py` — authentication/mode/rate-limit helpers.
- `backend/security/http_protection.py` — CSRF/HTTP protection helpers.
- `backend/security/credential_safety.py` — credential masking/safety utilities.
- `backend/security/safe_errors.py` — client-safe error helper.
- `backend/execution_guard.py`, `ccxt_guard.py`, `live_guard.py`, `live_trading_guard.py` — overlapping legacy guard surfaces; preserve until reference tracing is complete.

Admin live controls:
- global kill switch.
- bot-level LIVE control.
- AI-bot LIVE control.
- control audit.

Known defect: risk kill switch and real-order live-control kill switch are separate process-local control planes.

## 12. Admin functionality
`backend/admin.py` provides:
- administrative user/plugin/site/wallet/risk control surfaces.
- `/api/admin/live-controls/*`.
- AI Shadow evaluate/settle/monitor/feed controls.
- admin authentication/CSRF checks for live-control APIs.

Known architecture issue: `main.py` and `admin.py` instantiate separate CMSEngine objects, normally targeting the same SQLite file but with potential initialization/session drift.

## 13. Installer / setup functionality present but not fully exposed
Confirmed modules:
- `backend/installer.py`.
- `backend/install_service.py`.

Historical/status evidence indicates:
- first-admin creation service uses User/CMSEngine.
- installation marker prevents repeat installation.
- integration regression test exists.

Missing/incomplete exposure:
- HTTP `/install` route is not mounted/implemented in the current release contract.
- Production admin login still has a DEV bypass that must remain until a replacement installer/admin flow is complete.

## 14. Health / diagnostics / startup
Modules include:
- `backend/health.py`.
- `backend/health_check.py`.
- `backend/health_endpoint.py`.
- `backend/startup_check.py`.
- `healthcheck.py`.
- `backend/security/safe_errors.py`.

Known issue: historical audit found health routes defined but not mounted into `backend.main:app`; CI had false-positive checks that imported health functions instead of making real HTTP requests. Re-verify current main after the runtime restoration.

## 15. Market history / external data modules
- `backend/market_history.py` — market/news SQLite store and CCXT/RSS refresh pipeline.
- Public exchange data: ticker/order book/OHLCV.
- CoinDesk RSS news ingestion.
- Fixed keyword sentiment scorer.

The sentiment implementation is not an AI model.

## 16. Strategy performance / pricing
- `backend/strategy_performance.py` — strategy evaluation and license pricing/performance information.
- Marketplace consumes performance/catalog information.
- Backtest and strategy-performance data should not be conflated with live trading profitability.

## 17. Frontend/template surfaces
Active Jinja page routes include:
- `/`
- `/home`
- `/login`
- `/register`
- `/forgot-password`
- `/dashboard`
- `/settings`
- `/marketplace`
- `/bot-management`
- `/wallet`
- `/admin`

Active static mount is `frontend/` at `/static`.
Known market assets include:
- `style.css`
- `market_terminal.css`
- `market_live.css`
- `market_terminal.js`
- `market_live.js`
- `market_terminal_patch.js`

Non-authoritative/duplicate surfaces that must be preserved until dependency scan:
- root `static/` tree.
- `frontend/index.html` separate legacy/application surface.
- `frontend/pages/login.html` and `frontend/pages/register.html`.
- archive surfaces.

## 18. Deployment adapters
Present/configured historical surfaces include:
- Netlify + Mangum function.
- Docker.
- Render.
- Railway.
- Fly.io.
- Heroku/Procfile compatibility.
- Vercel.
- Codespaces/devcontainer.

Netlify runtime:
`netlify.toml → /.netlify/functions/api/:splat → netlify/functions/api.py → /tmp writable storage → Mangum → FastAPI`.

Codespace runtime:
`.devcontainer → Python runtime → requirements → run.py/uvicorn → port 8000`.

## 19. CI / test functionality
Present CI/test surfaces include:
- general CI workflow.
- CMS smoke workflow.
- deploy smoke workflow.
- sandbox smoke suite variants.
- installer regression test.
- strategy/execution security tests.
- health checks.
- exchange/CMSC rate-limit smoke tests.

Known issue: some historical CI checks tested helper functions rather than the actual HTTP route contract.

## 20. Functionality confirmed as missing / lost / not currently reachable
These are not to be invented as working features. They are recovery targets because evidence exists in modules/history/docs but the current UI/runtime does not fully expose them:
- HTTP installer `/install` and production first-admin flow.
- Complete CMSC debit/payment ledger for plugin purchases.
- Persistent strategy activation across restart/serverless lifecycle.
- Fully connected live order/cancel UI path through ExchangeService + execution gateway.
- Unified kill switch across RiskManager and LiveControlState.
- Actual background bot worker lifecycle behind start/stop.
- Authenticated simulation contract for `/api/bot/simulate`.
- Complete CSRF middleware for browser POST routes.
- Authoritative request/rate-limit policy wiring.
- Single authoritative execution-policy implementation after dependency tracing.
- Single authoritative exchange connection path.
- Full Telegram token validation/connection contract.
- Durable bot/brain runtime state if persistence is required.
- Complete UI exposure/verification for Dashboard, Wallet, Marketplace, Bot Management, Settings, Admin, Login/Register and theme modes.
- Any legacy/archived functionality that is referenced by callers but not yet traced.

## 21. Recovery rule
No item in section 20 is to be deleted or declared impossible until:
1. all branches are compared;
2. imports/callers/templates/tests are traced;
3. the historical implementation is identified;
4. the current contract is defined;
5. a minimal restoration is implemented without removing existing functionality;
6. unit/integration/HTTP/deployment tests pass.

## 22. Current audit priority
1. Restore and verify application boot/runtime.
2. Verify every page route and every API route against the template/JS caller.
3. Verify every service/domain dependency and DB/external call.
4. Resolve C-01..C-06.
5. Resolve H-01..H-10.
6. Resolve M-01..M-12.
7. Trace every legacy/duplicate surface before deletion.
8. Only then mark functionality DONE.
