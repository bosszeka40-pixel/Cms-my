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
- Netlify is not treated as the backend deployment target because this is a Python/FastAPI backend and Netlify preview deployment was failing on dependency/runtime compatibility.
- `.dockerignore` was added to reduce deployment context.
- `docker-compose.yml` was added for local/server Docker execution.
- `nixpacks.toml` was added with Python requirements install and Uvicorn start command.
- Deployment smoke workflow exists at `.github/workflows/deploy-smoke.yml`.
- Smoke workflow checks dependency installation, Python compilation, FastAPI import, and health/readiness functions.
- GitHub Actions did not create a workflow run for the tested commit, so a green CI result has NOT been claimed.
- A Vercel deployment attempt was blocked by a 403 authorization error for the available team scope. This is an access issue, not proof of an application failure.

## Netlify/CMSbot deployment context
- A newer CMSbot Netlify project was created by the user to avoid the older broken Netlify project and exhausted credits.
- The relevant successful preview/deployment commit used during the recent work was `0b6783d77c2ac5138d340ac9d43aff780bc90fe4`.
- Do not restart CMS development from an old branch just because an older branch has a familiar name. When resuming deployment work, first compare the current `main` and the exact commit/branch used by the successful CMSbot deployment.
- Netlify credits are limited; avoid repeated blind deploys. Prefer Codespace/GitHub Actions smoke tests before spending another Netlify build.

## Codespace continuation
- User works entirely from a phone; do not assume a PC, mouse, or desktop workflow.
- Screenshot/file-upload limits can block the user for hours. Prefer short terminal commands and ask for copied terminal text only when necessary; do not require screenshots for every step.
- User opened a fresh GitHub Codespace for `bosszeka40-pixel/Cms-my`.
- The Codespace has Python 3.12.14 and pip available.
- The Codespace environment currently reports `git: command not found`, so do NOT instruct the user to run `git pull` there unless Git has first been installed/confirmed.
- The Codespace exposed port is **8000**. The user's current forwarded URL was `https://super-carnival-4g46g96r4ghq7x9-8000.app.github.dev/`.
- Intended local start command is `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` after dependencies are installed.
- An attempted start produced `pydantic.errors.PydanticUndefinedAnnotation: name 'Request' is not defined`.
- Current GitHub `main` source already imports `Request` in the affected FastAPI modules, so this error is evidence that the Codespace's local source/dependency state does not exactly match the current GitHub source. Do not assume the source bug is still present without checking the actual file in the Codespace.
- An earlier attempt to use `.devcontainer/setup.sh` failed because that file does not exist; do not give that command again.
- `python -m pytest -q` also cannot be assumed available until `requirements.txt` has been installed in the current Codespace.
- Avoid creating another Codespace unless the current one is demonstrably unusable.

## Health/readiness
- Added `backend/health.py` with `/health` and `/ready` router endpoints.
- `/health` returns basic service status.
- `/ready` calls the existing market database setup (`ensure_table`) and reports readiness; failures should produce an unavailable status once the endpoint is running under FastAPI.
- Health router was connected in `backend/main.py` with `app.include_router(health_router)`.
- Current `backend/health.py` explicitly imports `Request` from FastAPI and uses it in endpoint annotations.

## Important testing rule
Never call a configuration file or a pending CI run a successful deployment. A deployment is considered verified only after an actual build/start and endpoint check (at minimum `/health` and `/ready`).

## Current continuation point
1. Use the existing fresh Codespace; do not start over.
2. Establish that the Codespace source matches the intended GitHub revision without relying on Git, because Git is currently unavailable there.
3. Install `requirements.txt` if dependencies are missing.
4. Start FastAPI on port 8000.
5. Verify `/health`.
6. Verify `/ready` and fix the real database-path/runtime issue if it appears.
7. Continue CMS function-by-function tracing, starting with the CMS currency purchase path and its existing credits/wallet integration.
8. Only after the real Codespace checks are clean, consider another Netlify deployment.

## Latest source/runtime notes
- `backend/health.py` on GitHub imports `Request` from FastAPI and defines strategy purchase, CMSC quote, and CMSC intent endpoints using it.
- `backend/cmsc_payment_api.py` also imports `Request` and contains CMSC payment intent/confirmation endpoints.
- `backend/rate_limit.py` imports `Request` and uses it in the rate limiter.
- Therefore the current `Request` error in Codespace should be treated as a local revision/import-state mismatch first, not immediately as a new application defect.

## Known branch context
Primary working branch used in earlier deployment work: `cleanup/security-hardening-2026-08`.
Recent construction branch also exists: `codex/final-cms-construction`.
Do not switch branches blindly; use the successful CMSbot deployment revision as the reference when choosing the working revision.
