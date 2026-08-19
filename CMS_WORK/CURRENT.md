# Current Work

## Active branch
`main`

## Current function
**Dashboard — CMSC balance display path**

## Full route to trace once
1. UI/template
2. JavaScript/event handlers
3. API endpoint
4. Router/controller
5. Service/domain logic
6. Database/storage
7. External integration if applicable
8. Response/error handling
9. UI state/update
10. Integration/regression test
11. Design consistency

## Status
- Overall: `IN PROGRESS`
- Deployment smoke: `DONE`
- Marketplace / Plugins — CMSC purchase path: `DONE`
- Dashboard CMSC balance display: `IMPLEMENTED — TESTING`
- Do not mark DONE until the complete route is verified.
- Do not start the next function until this branch is closed.

## Current implementation
- `/dashboard` requires an authenticated session and redirects unauthenticated users to `/login`.
- The dashboard obtains the authenticated user and calls `engine.get_or_create_wallet(user_email)`.
- Wallet data is converted to the dashboard dictionary contract, including `credits`, `provider`, `address`, and `telegram`.
- `dashboard.html` renders the CMSC balance from `wallet.credits`.
- Added `scripts/test_dashboard.py` to verify login → dashboard → CMSC balance rendering end-to-end.
- Added `.github/workflows/dashboard-smoke.yml` for repeatable CI verification.

## Cleanup rule
If code looks unused: mark candidate → search all references → run relevant tests → move if it belongs elsewhere → otherwise delete.

## Recovery
If chat history is lost, read `CMS_WORK/TREE.md` and this file first, then continue from the active branch.
