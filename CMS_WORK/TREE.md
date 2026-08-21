# CMS Work Tree — Strict Audit Update

Baseline: `main` @ `1b7fdd643ffd01e3da9f3ebc6682859568c76215`

## Mandatory closure chain

`UI/template → JS/event → API route → auth/CSRF/rate/risk gate → Router/controller → Service/domain → DB/Exchange → Response/error → UI state → Test → Deployment smoke → DONE`

A branch is not DONE because code exists. It is DONE only after the complete chain is verified.

## Function branches

- [ ] 01 Marketplace / Plugins — **RED / audit findings H-04/H-05/H-06/H-07**
- [ ] 02 Dashboard — **VERIFY required**
- [ ] 03 Wallet / CMSC — **RED / payment/accounting gap**
- [ ] 04 Bot management — **RED / process-local state and start/stop semantics**
- [ ] 05 Settings — **VERIFY / CSRF gap**
- [ ] 06 Admin — **VERIFY / split control planes**
- [ ] 07 Login/Register/Social login — **VERIFY / CSRF + install flow gaps**
- [ ] 08 Market / Candles / Live — **VERIFY / external-call/rate-limit/runtime checks**
- [ ] 09 Exchange connection / Trading — **RED / duplicate connection path + manual execution mismatch**
- [ ] 10 Database / persistence — **VERIFY / multiple SQLite paths**
- [ ] 11 Installer — **TODO / HTTP `/install` contract not mounted**
- [ ] 12 Error logging / diagnostics — **VERIFY / safe error helper not authoritative**
- [ ] 13 Legacy cleanup — **DO NOT DELETE; reference scan required**
- [ ] 14 Security / execution policy — **RED / duplicate policies and kill-switch split**
- [ ] 15 CI / deployment — **RED / health route + false-positive smoke tests + action drift**
- [ ] 16 Frontend/static assets — **VERIFY / duplicate `frontend/` and `static/` trees**
- [ ] 17 AI Shadow — **VERIFY / shadow path works conceptually; runtime and persistence still need end-to-end test**

## Working documents

- `TREE.md` — branch/function map
- `CURRENT.md` — active audit state
- `DECISIONS.md` — permanent decisions
- `ERRORS.md` — verified findings
- `LEGACY.md` — deletion candidates; do not delete blindly
- `CHECKLIST.md` — release gate
- `BRANCH_MAP_2026-08-21.md` — all Git branches and relations
- `FUNCTION_MAP_2026-08-21.md` — route/function map
- `CONNECTION_MAP_2026-08-21.md` — end-to-end logic/data connections
- `STRICT_AUDIT_2026-08-21.md` — full findings

## Branch rule

Do not merge whole divergent branches. Transfer only specific files/commits after tracing dependencies and running regression tests.

## Recovery rule

If chat history is lost, read:
1. `CMS_WORK/STRICT_AUDIT_2026-08-21.md`
2. `CMS_WORK/BRANCH_MAP_2026-08-21.md`
3. `CMS_WORK/FUNCTION_MAP_2026-08-21.md`
4. `CMS_WORK/CONNECTION_MAP_2026-08-21.md`
5. `CMS_WORK/CURRENT.md`
6. `CMS_WORK/ERRORS.md`

Then continue from the first OPEN critical finding; do not restart the project.
