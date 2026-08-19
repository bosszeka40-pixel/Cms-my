# Current Work

## Active branch
`cleanup/security-hardening-2026-08`

## Current function
**Marketplace / Plugins**

## Work log — 2026-08-19
- Created rollback point before integrating deployment fixes: `rollback-before-full-5b0b93c`.
- Reviewed commit `5b0b93c5f759c8b47e9576f8679cb65af4ee9aa6` and compared its intended deployment/startup fixes with the current branch.
- Reviewed `main` as a source of already-integrated fixes; did **not** blindly merge `main` because the current branch contains newer security hardening that must not be downgraded.
- Preserved newer security settings such as fail-closed execution policy, HFT risk controls, `SECRET_KEY`, and `SESSION_HTTPS_ONLY`.
- Added/retained deployment and health/readiness fixes where they were compatible with the current branch.
- Confirmed `requirements.txt` already contains `pytest`, so the older CI finding about missing pytest is no longer current.
- Found stale `.gitmodules` metadata referencing a missing `Cms` submodule. Removed `.gitmodules` in commit `d83dafad25f00dede06f7c5e6268a103ecefd860` because the `Cms/` path is absent from the branch.
- Found that `.github/workflows/cms-smoke.yml` only triggered on `main`, so the security branch could not produce its own smoke run. Updated it in commit `5a40e6f2cf71002543a781af387d61dbf2af695b5` to trigger on both `main` and `cleanup/security-hardening-2026-08`, and on PRs targeting either branch.
- Current smoke workflow runs dependency install, Python compile, `healthcheck.py`, application startup, `/health`, and `/ready` checks.
- CI still needs fresh verification after the workflow trigger fix; absence of a run is not treated as a pass.
- Netlify deploy-preview previously failed during `Install dependencies`; exact package-level cause still needs deploy-log evidence before changing dependencies.

## What remains to do
1. Verify the new smoke workflow run for `5a40e6f2cf71002543a781af387d61dbf2af695b5`.
2. If CI fails, inspect the failing job/log and fix the root cause only.
3. Obtain/inspect the Netlify dependency-install error details before changing `requirements.txt` or build configuration.
4. Verify Docker startup and `/health` + `/ready` end-to-end.
5. Compare remaining `main` differences file-by-file; transfer only compatible fixes, never downgrade security hardening.
6. Review `backend/main.py`, `backend/hft_brain.py`, and `requirements.txt` against the integrated `main` changes.
7. Continue Marketplace / Plugins route verification through UI → JS → API → backend → storage/integration → response/error → UI update → regression test.
8. Update this file after each material change and record the next required action.

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
- Do not mark DONE until the complete route is verified.
- Do not start the next function until this branch is closed.

## Cleanup rule
If code looks unused: mark candidate → search all references → run relevant tests → move if it belongs elsewhere → otherwise delete.

## Recovery
If chat history is lost, read `CMS_WORK/TREE.md` and this file first, then continue from the active branch.
