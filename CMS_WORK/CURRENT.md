# Current Work — Strict Audit

Date: 2026-08-21

## Update 2026-08-29 (UI-полировка, отдельный трек)
- Сейчас: единый красивый рендер API-панелей через `static/api_render.js` (ApiUI) — карточки/таблицы/бейджи/гейджи на 6 страницах. Backend не тронут.
- Git: работа на ветке `jeevgenij-coder-cms` (fast-forward → `08fd3c4`, коммит ApiUI). Push в GitHub ожидает авторизации (нет токена/SSH на машине).
- Документы: `SUMMARY_2026-08-29.md`, `ACTIONS_LOG_2026-08-29.md`, `UI_RENDER_2026-08-29.md`, `GIT_STATUS_2026-08-29.md`.
- Продолжение аудита (список ниже) не выполнялось — это отдельный трек строгого аудита.

## Active baseline
`main` @ `1b7fdd643ffd01e3da9f3ebc6682859568c76215`

## Current phase
**Strict full repository audit before further functional changes.**

The project is **NOT DONE** and must not be declared production-ready.

## What has been audited

- all Git branches listed in the repository;
- current FastAPI routes in `backend/main.py`;
- admin router routes in `backend/admin.py`;
- CMSEngine models and persistence paths;
- StrategyManager/DailyCompoundHarvester;
- RiskManager;
- HFTBot and CMSProductionHFTBot/AICryptoMemoryBrain;
- AI Shadow trader/feed;
- ExchangeService and real-order gateway;
- execution policies/live controls/request policy/credential safety;
- market history/news pipeline;
- Jinja templates and active frontend static mount;
- duplicate `static/` and `frontend/` assets;
- Codespace startup files;
- Netlify/Vercel/Docker/Render/Railway/Fly/Procfile deployment contracts;
- CI and smoke workflows;
- existing regression tests;
- branch divergence and rollback points.

## Current blockers

1. `/health` and `/ready` are defined but not mounted into the FastAPI application.
2. `/api/bot/simulate` is unauthenticated while regression tests require anonymous 401.
3. `/api/user/connect-exchange` is unauthenticated and duplicates ExchangeService.
4. Main browser POST routes do not have a global CSRF contract.
5. RiskManager kill switch and real-order LiveControlState kill switch are separate.
6. `/api/trading/manual` reports `executed` without exchange execution.
7. Plugin purchase does not debit CMSC or create a payment ledger.
8. Strategy activation is not persisted and unknown strategies fall back to pure_harvester.
9. Telegram token field is ignored by the backend.
10. Bot/HFT/AI memory is process-local and bot start/stop does not create a real loop.
11. CI health checks do not prove actual `/health` and `/ready` routing.
12. Active frontend assets are duplicated with a second root `static/` tree.

## Required method

For every fix:

`reproduce → identify root cause → change minimum code → preserve all unrelated functionality → add/update regression test → run full suite → run real HTTP smoke → inspect response → record result here/ERRORS.md`.

## No blind merges

Divergent branches are reference material, not merge targets. Recover useful fixes file-by-file/commit-by-commit only after dependency tracing.

## No deletion

Do not delete legacy/duplicate code during this audit. Record candidates in `CMS_WORK/LEGACY.md`; deletion requires a separate dependency/reference/test gate.

## Recovery

Read `CMS_WORK/STRICT_AUDIT_2026-08-21.md`, `BRANCH_MAP_2026-08-21.md`, `FUNCTION_MAP_2026-08-21.md`, and `CONNECTION_MAP_2026-08-21.md` before continuing.
