# CMS Work — Chat History / Continuation Log

## Purpose
This file preserves the available project decisions and work context so the CMS can be continued after chat-history loss. It is not a verbatim export of hidden or unavailable chat messages.

## Core workflow agreed
- Work on the CMS continuously and in ordered passes.
- Take one function at a time and trace its complete path through the CMS before moving to the next function.
- Mark a completed function branch as completed so it is not repeatedly rechecked from different angles.
- Use helper tools/agents in parallel where useful: one checks connections, another checks whether functions exist in templates/site, another adds missing functionality, another handles design.
- Keep work records in `CMS_WORK/` so the project can be resumed by asking to inspect that folder.
- Do not use simulations when a real integration/deployment test is possible.

## CMS currency decisions
- CMS internal currency is valued at exactly **1 CMS = 1 EUR**.
- Users can purchase CMS currency using USDT or other supported currencies.
- Exchange calculates the required amount using the current exchange rate, minus the configured commission.
- Exchange functionality is intended specifically for CMS currency purchase/exchange.
- Purchase does not require an admin request.
- Withdrawal is separate and is **only by request to an administrator**.
- Withdrawal commission/tax/necessary settings belong in the admin panel.
- Withdrawal work is postponed for now.
- CMS balance must be the existing wallet/credits balance; do not create a duplicate wallet system.
- Bot access is API-based; it is not an independent direct purchase/withdrawal mechanism.

## Deployment work
- Goal: make the CMS deployable and genuinely testable on multiple platforms.
- Primary portable deployment target: Docker.
- Deployment configurations prepared/considered for Render, Railway, Fly.io, Heroku-compatible PaaS, Vercel where compatible, Nixpacks, Docker Compose, and generic Docker hosts.
- Netlify is not treated as the backend deployment target because this is a Python/FastAPI backend and Netlify preview deployment was failing.
- `.dockerignore` was added to reduce deployment context.
- `docker-compose.yml` was added for local/server Docker execution.
- `nixpacks.toml` was added with Python requirements install and Uvicorn start command.
- Deployment smoke workflow exists at `.github/workflows/deploy-smoke.yml`.
- Smoke workflow checks dependency installation, Python compilation, FastAPI import, and health/readiness functions.
- GitHub Actions did not create a workflow run for the tested commit, so a green CI result has NOT been claimed.
- A Vercel deployment attempt was blocked by a 403 authorization error for the available team scope. This is an access issue, not proof of an application failure.

## Health/readiness
- Added `backend/health.py` with `/health` and `/ready` router endpoints.
- `/health` returns basic service status.
- `/ready` calls the existing market database setup (`ensure_table`) and reports readiness; failures should produce an unavailable status once the endpoint is running under FastAPI.
- Health router was connected in `backend/main.py` with `app.include_router(health_router)`.

## Important testing rule
Never call a configuration file or a pending CI run a successful deployment. A deployment is considered verified only after an actual build/start and endpoint check (at minimum `/health` and `/ready`).

## Current continuation point
1. Run a real deployment/start test using an authorized provider.
2. Verify `/health`.
3. Verify `/ready`.
4. Fix actual build/runtime errors only after seeing them.
5. Then continue CMS function-by-function tracing, starting with the CMS currency purchase path and its existing credits/wallet integration.

## Known branch context
Primary working branch used in the recent deployment work: `cleanup/security-hardening-2026-08`.

## Recent commits mentioned during work
- `f0c5d44` — Render deployment configuration adjustment.
- `e5930ac` — deployment smoke workflow extension.
- Later changes added health router, Docker/Nixpacks/Compose support; exact commit IDs should be checked from Git history rather than assumed from this log.
