# CMS-my — STRICT FULL AUDIT 2026-08-27

## Purpose
This document is the strict recovery/audit gate for the CMS before any further product development. It supplements the 2026-08-21 audit and must be read together with FUNCTION_MAP, CONNECTION_MAP, BRANCH_MAP and AI_CODER_MASTER_SPEC.

## Audit rule
No feature is accepted because a function exists. A feature is PASS only when the complete chain is proven:

`UI/template -> JS/form -> route -> auth -> CSRF -> rate limit -> mode/risk -> controller/service -> persistence/external API -> response contract -> UI state -> test -> real HTTP smoke -> deployment runtime`.

No deletion during recovery. No wholesale branch merge. No silent change of strategy semantics. No LIVE execution outside the single guarded execution path.

## Current repository topology
The repository has a large parallel branch history. Branch inventory captured from GitHub includes:
- main
- audit/strict-2026-08-21
- backup/2026-08-19-all-work
- backup/2026-08-19-work-state
- chore/mece-opencode-setup
- ci/real-cms-smoke
- cleanup/cmsc-exchange-security-final
- cleanup/security-hardening-2026-08
- codespace-special-zebra-r7r9pp46qw6xhwwqx
- codex/-github
- codex/final-cms-construction
- dependabot/pip/email-validator-2.3.0
- dependabot/pip/pydantic-2.13.4
- dependabot/pip/pyyaml-6.0.3
- dependabot/pip/uvicorn-0.52.3
- dependabot/pip/werkzeug-3.1.8
- fix/ci-failures
- fix/ci-runtime-2026-08-21
- fix/codespace-local-runtime-2026-08-21
- fix/netlify-python312-cmsc
- fix/sandbox-smoke-suite
- fix/sandbox-smoke-suite-v2
- fix/sandbox-smoke-suite-v3
- fix/sandbox-smoke-suite-v4
- fix/sqlite-ci-runtime
- integrate-main-fixes-safe
- restore/working-runtime-2026-08-20
- rollback-before-full-5b0b93c
- rollback-before-full-5b0b93c-2026-08-19
- temp-full-5b0b93c
- v0/ci-failure-investigation-d211849a
- work/connect-exchange-security
- work/connect-exchange-security-ci
- work/connect-exchange-security-ci2

Branch rule: branches are evidence/reference, not merge instructions. Compare and trace before taking any change.

## Confirmed architecture
### Core
- FastAPI + Jinja2 application.
- Session authentication and roles.
- Google/GitHub OAuth state validation.
- Telegram HMAC login.
- Password authentication with migration layer.
- Admin router.
- CMSEngine persistence for users/plugins/access/memory/stats/audit/wallet/trades/settings.

### Trading domain
- StrategyManager and DailyCompoundHarvester.
- RiskManager.
- HFTBot.
- CMSProductionHFTBot/AICryptoMemoryBrain.
- AI Shadow trader/feed.
- ExchangeService.
- Security execution policy, gateway and live controls.

### Market domain
- Public CCXT ticker/order book/OHLCV.
- Market history SQLite.
- RSS/news and keyword sentiment.
- Market signal generation.
- Chart/live terminal assets.

### Deployment
- Codespace/devcontainer.
- Netlify/Mangum adapter.
- Docker/Render/Railway/Fly/Procfile/Vercel adapters.

## Critical defects to resolve before release
### C-01 Health routing
`backend/health.py` defines health endpoints but the application must explicitly mount and verify them through HTTP. Import-only health tests are insufficient.

### C-02 Unauthenticated simulation
`/api/bot/simulate` must require authenticated user/session and appropriate non-LIVE mode. Anonymous access must be rejected.

### C-03 Duplicate exchange connection path
The marketplace/direct `/api/user/connect-exchange` path must not bypass ExchangeService, credential safety, request policy, sandbox handling and audit. Establish one authoritative connection service.

### C-04 Browser CSRF
All state-changing browser POST routes must use one consistent CSRF contract. Admin live controls already have a specific check; general browser forms need equivalent protection.

### C-05 Split kill switches
RiskManager kill switch and LiveControlState global kill switch must be unified semantically. A global LIVE block must prevent every new LIVE order regardless of caller. Emergency cancel remains a separate explicit operation.

### C-06 Manual trading semantic error
`/api/trading/manual` must never return `executed` unless an order was actually submitted/confirmed. Preserve simulation behavior under DEMO/PAPER; use explicit LIVE gateway for real orders.

## High defects
### H-01 Duplicate execution guards
Trace and select one authoritative execution-policy path. Legacy guards remain until reference/test analysis proves they are dead.

### H-02 Request policy not authoritative
Authentication, rate limiting, mode restrictions and safe client errors must be applied consistently at the route boundary.

### H-03 Raw provider exceptions
Do not return raw CCXT/provider/database exception strings to users. Log server-side with correlation ID; return stable safe error codes/messages.

### H-04 CMSC accounting
Plugin purchase must atomically validate price, debit CMSC, create payment/ledger record and grant/extend access. Failed debit must grant no access.

### H-05 Strategy identity/execution mismatch
Every activated strategy must have an executable implementation or be explicitly marked unavailable. Unknown strategy names must never silently fall back to another strategy.

### H-06 Strategy persistence
Activated strategy/config must persist in database/config storage and survive process restart/serverless lifecycle.

### H-07 Telegram contract
If UI requests token + username, backend must validate the complete contract or remove the unused field from UI. Never claim a connection without validation.

### H-08 Process-local bot state
Durable bot configuration, state, positions, order IDs, heartbeats, PnL and lifecycle events must be persistent. Runtime caches may remain process-local.

### H-09 Bot lifecycle
Start/pause/resume/stop must control a real worker/runtime lifecycle. A boolean flag alone must not be presented as an active running bot.

### H-10 Multiple CMSEngine instances
Centralize database/session configuration so main/admin/services do not drift across separate initialization paths.

## Medium defects
- Relative SQLite paths create environment-dependent databases.
- Core DB and market DB need explicit deployment persistence policy.
- Synchronous external CCXT/RSS calls can block request workers.
- Expensive market endpoints need rate limits/cache.
- Keyword sentiment must be labelled as heuristic, not model-grade AI.
- Backtest ROI must use a correctly named period metric.
- `frontend/` is active static tree; root `static/` is duplicate/legacy until proven otherwise.
- `frontend/index.html` is a duplicate application surface and must not bypass the authoritative API.
- Root template data contract must provide every variable it expects.
- Deployment docs and health routes must agree.
- CI must execute real HTTP health/API smoke, not only import functions.

## Required audit matrix
For every route/function, record:
1. Caller/UI.
2. Authentication and role.
3. CSRF requirement.
4. Rate limit.
5. Execution mode.
6. Risk gate.
7. Domain service.
8. Database tables/state.
9. External API calls.
10. Success response schema.
11. Error response schema.
12. Frontend consumer.
13. Unit/integration/HTTP test.
14. Deployment adapter.
15. Failure/rollback behavior.

## Recovery priorities
1. Boot/runtime/import integrity.
2. Real HTTP `/`, `/health`, `/ready`.
3. Authentication/session/CSRF.
4. Database initialization and persistence.
5. Existing market terminal.
6. Existing strategies/risk/test/backtest.
7. ExchangeService and capability registry.
8. Demo/Paper/Backtest/Shadow execution separation.
9. Real LIVE gateway and kill switch.
10. Durable bot runtime.
11. User profile/wallet/settings.
12. Professional terminal UI placement without redesigning the visual language.
13. Copy trading.
14. Full regression/E2E/deployment smoke.

## Release gate
A build is RED if any critical path is untested, any LIVE path bypasses the gateway, any secret is exposed, any route lies about execution status, or any UI calls a duplicate unsafe implementation.

A build is GREEN only with evidence for BUILD + UNIT + INTEGRATION + HTTP + UI + DB + EXCHANGE + BOT + STRATEGY + RISK + SECURITY + DEPLOYMENT.
