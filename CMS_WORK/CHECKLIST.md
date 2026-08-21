# CMS Work Checklist

## Per-function closure
- [ ] UI/template exists and is the active template
- [ ] JavaScript/event handlers are connected
- [ ] API endpoint exists and matches frontend contract
- [ ] Router/controller reaches the correct service
- [ ] Service/domain logic is implemented once (no duplicate source of truth)
- [ ] DB/storage dependencies are verified
- [ ] External integration dependencies are verified when applicable
- [ ] Success and error responses reach the UI correctly
- [ ] UI state updates correctly
- [ ] Mobile/light/dark design is consistent
- [ ] Integration/regression test passes
- [ ] Branch marked DONE in TREE.md and PROJECT_STATUS.md

## Strict release gate — 2026-08-21
- [ ] `/health` is actually mounted and returns 200 through `app`
- [ ] `/ready` is actually mounted and returns 200 through `app`
- [ ] Anonymous `/api/bot/simulate` returns 401
- [ ] Anonymous `/api/user/connect-exchange` is rejected
- [ ] One authoritative exchange-connection path is selected
- [ ] Browser POST CSRF contract is applied consistently
- [ ] Virtual endpoints reject explicit LIVE mode
- [ ] Risk kill-switch and LIVE control have one authoritative emergency-stop contract
- [ ] Manual trade semantics match actual execution mode
- [ ] Real orders can only pass through execution_gateway
- [ ] Plugin purchase has a verified CMSC/payment/ledger contract before charging users
- [ ] Activated strategy is executable and persisted
- [ ] Telegram UI fields match backend behavior
- [ ] Process-local bot state is not presented as durable production state
- [ ] Market/news expensive endpoints have rate/error policy
- [ ] Duplicate static/template trees are reconciled without deleting functionality
- [ ] CI tests real HTTP routes instead of only importing helper functions
- [ ] Full pytest suite passes
- [ ] Full unittest suite passes
- [ ] Codespace startup passes on Python 3.12 / port 8000
- [ ] Netlify runtime passes if Netlify is used
- [ ] No existing CMS function is lost

## Cleanup
- [ ] Suspicious code marked CANDIDATE before deletion
- [ ] All references searched
- [ ] Tests checked
- [ ] Moved if required elsewhere
- [ ] Deleted only after dependency check
