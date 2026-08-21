# CMS-my — STRICT FULL AUDIT

Date: 2026-08-21
Audited baseline: `main` @ `1b7fdd643ffd01e3da9f3ebc6682859568c76215`
Scope: current main, all 30 other branches, backend routes/functions, security boundaries, database/storage, templates, frontend/static assets, deployment adapters, CI, tests, and UI→JS→API→service→storage/external→response chains.

## Status
**RED / NOT RELEASE READY.**

The repository contains substantial working functionality, but current `main` has contract mismatches between code, tests, deployment configuration and UI. No functionality was deleted during this audit. This file records findings; fixes must be made one root cause at a time and re-tested.

## Critical findings

### C-01 — `/health` and `/ready` are not mounted into the FastAPI app
`backend/health.py` defines both endpoints, but `backend/main.py` does not include `health.router` and has no equivalent routes. CI curls both routes. Render, Railway and Fly also use `/health`. `DEPLOYMENT.md` instead says `/` is the common health endpoint. Result: deployment health checks can fail even when Python starts. **CRITICAL.**

### C-02 — `/api/bot/simulate` is unauthenticated
The handler accepts market/AI arrays and runs HFT simulation without a session check. `tests/test_smoke.py` and `tests/test_cms_health.py` explicitly require anonymous access to return 401. Result: code contradicts its own regression contract and exposes a compute endpoint. **CRITICAL.**

### C-03 — `/api/user/connect-exchange` bypasses the central ExchangeService/security architecture
The route directly instantiates CCXT, accepts raw API credentials, and calls `load_markets()` without authentication, request policy, credential-safety helper, ExchangeService, or live-control integration. It does not persist the secret, which is positive, but the public endpoint is still unsafe and duplicated. **CRITICAL.**

### C-04 — Main browser POST routes have no CSRF protection
Affected: `/login`, `/register`, `/dashboard`, `/settings`, `/marketplace`, `/bot-management`, `/wallet`, `/admin`, `/admin/risk`. Admin live-control API has its own CSRF check, but that does not protect the browser POST surface globally. `http_protection.py` contains CSRF helpers but is not installed as middleware. **HIGH/CRITICAL.**

### C-05 — Risk kill-switch and real-order kill-switch are different control planes
`/api/risk/kill-switch` changes `RiskManager.kill_switch`. Real exchange execution requires `LiveControlState.global_kill_switch`, bot-level LIVE state, and `security/execution_policy.py`. These are independent process-local states. **CRITICAL safety-contract mismatch.**

### C-06 — `/api/trading/manual` reports `executed` without executing an exchange order
It validates input, calculates a fee, records a Trade/audit entry and returns `status=executed`; it never calls ExchangeService or an exchange order method. **CRITICAL product-contract mismatch.** Do not turn it into LIVE trading until the explicit gateway is integrated.

## High findings

### H-01 — Duplicate execution policy implementations
`backend/execution_guard.py` and `backend/security/execution_policy.py` define overlapping trading modes/policies. The gateway uses the security version while AI Shadow uses execution_guard. **HIGH.**

### H-02 — Request-policy security helpers are not authoritative
`backend/security/request_policy.py` provides authentication, virtual-mode rejection, rate limiting and safe client errors, but main endpoints implement ad-hoc checks and raw error responses. **HIGH.**

### H-03 — Internal/provider exceptions are returned to clients
Exchange, market, news and registration handlers include raw `str(exc)` in HTTP responses. A safe-error helper exists but is not consistently used. **HIGH.**

### H-04 — Plugin purchase does not debit CMSC balance
`CMSEngine.purchase_plugin()` creates/extends UserPlugin access but does not subtract price from Wallet. No payment/ledger record is created. The marketplace nevertheless displays a CMSC balance and EUR prices. **HIGH.**

### H-05 — Plugin activation can claim a strategy is active while execution falls back to another strategy
Activation accepts any existing plugin and writes its name to config. `StrategyManager.execute()` implements only pure_harvester, high_frequency_momentum and compound_defender; unknown names silently fall back to pure_harvester. Learned/extra strategy names therefore are not proof of executable strategy logic. **HIGH.**

### H-06 — Strategy activation is not persisted
`/api/strategies/activate` modifies in-memory config only and does not call `save_strategy_config()`. Restart/serverless lifecycle loses the selected strategy. **HIGH.**

### H-07 — Telegram UI asks for a bot token but backend ignores it
`templates/marketplace.html` contains `telegram_token`, but the handler reads only `telegram_username`. The UI can therefore report a connection without validating/using the supplied token. **HIGH.**

### H-08 — HFT/bot/brain state is process-local
`HFTBot.stats`, `CMSProductionHFTBot.capital`, `trade_history`, and `AICryptoMemoryBrain.memory_history` disappear on restart. Persistent LearningMemory/Trade is separate. **HIGH continuity gap.**

### H-09 — Bot start/stop only toggles state
`HFTBot.start()` and `stop()` set a boolean and append an event. They do not start/stop a background market/trading loop. UI wording can imply a running bot when only state changed. **HIGH.**

### H-10 — Main and admin create separate CMSEngine instances
Both instantiate their own SQLAlchemy engine/session objects. They normally target the same default SQLite file, but initialization/migration/session state can drift. **MEDIUM/HIGH architecture risk.**

## Medium findings

### M-01 — Core database location depends on current working directory
CMSEngine's default is `sqlite:///./cms_core.db`. Netlify changes cwd to `/tmp`; local/Docker/PaaS paths therefore differ. **MEDIUM.**

### M-02 — CMS and market data use separate SQLite databases
Core state uses `cms_core.db`; market data uses `cms_v12.db`. Deployment persistence/backup must account for both. **MEDIUM.**

### M-03 — Synchronous HTTP handlers perform CCXT network calls and SQLite writes
Market data/history/signal and marketplace performance can refresh external data inside request handlers. Slow provider calls can consume worker capacity. **MEDIUM.**

### M-04 — Market/news endpoints do not use the existing rate-limit helper
A rate-limit implementation exists but is not wired into these expensive endpoints. **MEDIUM.**

### M-05 — News sentiment is a fixed keyword scorer, not an AI model
The implementation uses a small positive/negative word set. Product/UI wording must not imply model-grade sentiment analysis. **MEDIUM.**

### M-06 — Backtest `roi` is sourced from a field named monthly_return_pct while backtesting up to 365 daily candles
`/api/bot/backtest` uses `daily[-365:]` and returns that field as `roi`; this is potentially a one-year result presented as monthly. **MEDIUM reporting correctness.**

### M-07 — Duplicate static trees
Both `frontend/` and `static/` contain market/style assets. `main.py` mounts `frontend/` as `/static`, so changes under `static/` are not the active FastAPI assets. **MEDIUM/HIGH maintenance risk.**

### M-08 — Duplicate application surface in `frontend/index.html`
The actual `/` route renders `templates/index.html`, while `frontend/index.html` contains a separate exchange-connection UI and posts directly to the unsafe `/api/user/connect-exchange`. **MEDIUM/HIGH UI drift.**

### M-09 — Root template expects `user_name`, root handler does not provide it
Authenticated `/` renders `user_name` but `serve_root()` only supplies `request` and `user_id`. **LOW/MEDIUM.**

### M-10 — Deployment documentation contradicts health configuration
`DEPLOYMENT.md` says `/` is the common health endpoint while Render/Railway/Fly/CI use `/health`; `backend/health.py` defines `/health`/`/ready` but is not mounted. **HIGH documentation/config drift.**

### M-11 — CI action versions regressed relative to CMS_WORK history
Current `ci.yml` and `deploy-smoke.yml` use `actions/checkout@v4` and `actions/setup-python@v5`, while `CMS_WORK/CURRENT.md` records a previous update to v5/v6. **MEDIUM.**

### M-12 — deploy-smoke verifies health functions directly instead of HTTP routes
It imports `health()` and `ready()` and prints them; it does not start the app and request `/health`/`/ready`. This can pass while the application routes are absent. **HIGH false-positive test.**

## Legacy / duplication candidates — DO NOT DELETE YET
- `static/` versus active `frontend/` static mount.
- `frontend/index.html` versus `templates/index.html`.
- `backend/execution_guard.py` versus `backend/security/execution_policy.py`.
- HFTBot simulation path versus CMSProductionHFTBot path.
- Inline marketplace exchange connection versus `ExchangeService`.
- `backend/health.py` versus direct health routes if added later.
- `frontend/pages/login.html` and `frontend/pages/register.html` versus Jinja templates.
- `frontend/Untitled-1` — no dependency established yet.
- `archive/` — preserve until reference scan proves it is dead.

## Existing functionality confirmed in code
- FastAPI + Jinja application.
- Session authentication and OAuth state checks.
- Password scrypt migration layer.
- Persistent users/plugins/access/memory/wallet/trades/site settings/audit logs.
- Public CCXT market data.
- Strategy manager and risk manager.
- Separate real-order gateway with fail-closed LIVE policy.
- Admin LIVE controls with CSRF.
- AI Shadow paper-only orchestration.
- Docker/Render/Railway/Fly/Heroku/Vercel/Netlify adapters.

## Release gate
Resolve and test **C-01..C-06**, then **H-01..H-10**, then **M-01..M-12**. Every fix must preserve existing functionality and add/update regression coverage where a contract changes.
