# CMS Test / Server Errors

Persistent record of verified code/configuration/test mismatches. This audit does not mark a finding fixed until the actual application route is tested.

## 2026-08-21 — strict repository audit

### C-01 — health/readiness routes not mounted
- Environment: main / CI / Render / Railway / Fly
- Route/function: `/health`, `/ready`
- Error: `backend/health.py` defines routes but `backend.main:app` does not include its router.
- Reproduction: start `backend.main:app` and request `/health` or `/ready`.
- Root cause: health router exists as a separate module but is not registered in main.
- Fix: OPEN — do not implement here until route contract is agreed.
- Verification: not run against a live app.
- Status: OPEN

### C-02 — bot simulation authentication mismatch
- Environment: main / tests
- Route/function: `POST /api/bot/simulate`
- Error: route has no session check; tests require anonymous 401.
- Reproduction: POST valid `market_data`/`ai_stream` without session.
- Root cause: auth policy omitted from handler.
- Fix: OPEN.
- Verification: static code inspection + regression test contract.
- Status: OPEN

### C-03 — direct exchange connection bypass
- Environment: main
- Route/function: `POST /api/user/connect-exchange`
- Error: unauthenticated direct CCXT route duplicates `ExchangeService` and bypasses request/security policy.
- Root cause: legacy inline implementation remained after central exchange service/security architecture was added.
- Status: OPEN

### C-04 — browser POST CSRF gap
- Environment: main
- Routes: login/register/dashboard/settings/marketplace/bot-management/wallet/admin/admin-risk
- Error: no CSRF check on normal browser state changes.
- Root cause: CSRF exists only for admin live-control API and as unused helper module.
- Status: OPEN

### C-05 — kill-switch control-plane mismatch
- Environment: main
- Routes: `/api/risk/kill-switch` vs `/api/admin/live-controls/global`
- Error: two independent kill-switch states exist.
- Root cause: RiskManager and LiveControlState were added as separate safety layers without a unified authoritative stop contract.
- Status: OPEN

### C-06 — manual trading semantic mismatch
- Environment: main
- Route: `POST /api/trading/manual`
- Error: response says `executed` but no exchange order is submitted.
- Root cause: route is local accounting/simulation while API wording implies execution.
- Status: OPEN

### H-04 — plugin purchase accounting gap
- Route: marketplace `buy_plugin`
- Error: purchase/access is recorded without CMSC debit or payment ledger.
- Status: OPEN

### H-05/H-06 — strategy activation gap
- Route: `/api/strategies/activate`
- Error: unknown strategy names can be marked active but StrategyManager falls back to pure strategy; selected strategy is not persisted.
- Status: OPEN

### H-07 — Telegram form/backend mismatch
- Route: marketplace Telegram connection
- Error: UI collects `telegram_token`, backend ignores it and stores only username.
- Status: OPEN

### H-08/H-09 — bot runtime is process-local
- Functions: HFTBot, CMSProductionHFTBot, AICryptoMemoryBrain
- Error: start/stop and memory/history do not survive restart; HFTBot start/stop does not create a trading loop.
- Status: OPEN

### M-11/M-12 — CI drift and false-positive health check
- Files: `.github/workflows/ci.yml`, `.github/workflows/deploy-smoke.yml`
- Error: action versions are older than the documented CMS_WORK state; deploy-smoke imports health functions instead of testing HTTP routes.
- Status: OPEN

## Audit rule
No finding is `FIXED` until the route/function is exercised, regression-tested, and the result is recorded here.
