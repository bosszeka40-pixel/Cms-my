# CMS Work Decisions

1. Work is function-by-function, not file-by-file.
2. Each function must be traced end-to-end before being marked `DONE`.
3. Completed branches are not re-audited unless a new test/error reopens them.
4. Existing functionality must be preserved unless a dependency check proves it is obsolete.
5. Suspected legacy code is never deleted by appearance alone.
6. Simulation/paper trading is not the final trading flow; it is only test support until live flow is verified.
7. Functional testing comes before the dedicated security phase.
8. Helper tools may work in parallel on separate boundaries; conflicting edits must be reconciled before closure.
9. Work-state documents for this phase live in `CMS_WORK/` so the project can be recovered without chat history.
10. Server deployment/testing must produce a persistent error log that is tracked in `CMS_WORK/ERRORS.md` when available.
11. (2026-08-29) UI-полировка выполняется ТОЛЬКО в `templates/*` + `static/*` единым модулем `static/api_render.js`; backend и системные файлы не изменяются. Данные — из существующих API через fetch; формы ответов сверяются с реальными ответами сервера перед рендером.
