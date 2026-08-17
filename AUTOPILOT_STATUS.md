# Autopilot Status

Updated: 2026-08-17

## Current branch

`cleanup/security-hardening-2026-08`

## Current checkpoint

Latest live-control commits: `1bec08f` and `951ab70`
PR: #2 (do not merge automatically)

## Autopilot mode

Continuous safe execution: after each meaningful checkpoint, continue with the next reversible implementation/validation task. Stop only for an unsafe irreversible action, required human approval, or genuinely missing information.

## Completed in this autopilot pass

- Oi Operating Brief + Execution Planning + Risk Review loaded for continuous project work.
- Oi Quality Review remains active for the project checkpoint.
- Added `pytest==8.3.5` to `requirements.txt`; prior CI run `32012192724` passed.
- Added `backend/security/request_policy.py` with reusable authentication, virtual-execution and client-safe-error helpers.
- Added `tests/test_request_policy.py` covering anonymous rejection, authenticated identity, LIVE-header rejection and safe errors.
- Added `backend/security/live_controls.py` with fail-closed global kill switch, per-bot LIVE state, per-AI-bot LIVE state, explicit admin actor attribution, and audit entries.
- Added `tests/test_live_controls.py` covering default-off behavior, global kill switch, per-bot enablement, per-AI-bot enablement, fail-closed assertion, and audit logging.
- Existing execution policy, execution gateway and CCXT guard remain preserved.
- Existing bot / AI / memory / strategy functionality remains protected from replacement.

## Verified / still open

- The new LIVE control module is unit-tested in source but has not yet appeared in a GitHub Actions run for the latest commits; run CI and inspect results.
- `/api/user/connect-exchange` still needs to call the request authentication helper and stop returning provider exception text.
- `/api/bot/simulate` still needs authenticated virtual/sandbox enforcement.
- Manual and strategy execution paths still require explicit central execution-mode/kill-switch boundaries.
- The new request-policy helpers are covered by tests but not yet wired into the affected routes.
- The new LIVE controls are not yet wired into the admin API/UI or execution gateway; this is the next functional security step after CI verification.
- Template-to-route/API functional coverage audit remains in progress.
- `Cms` appears as a gitlink/submodule entry while `.gitmodules` is absent; do not invent a remote URL. Resolve metadata only after the intended submodule source is identified.
- Netlify deploy-preview remains a separate verification gate.

## Autopilot safety gates

1. No merge to `main` without explicit user approval.
2. LIVE capability may exist in production code, but it remains disabled by default and must never be silently enabled.
3. No real orders are sent during tests.
4. Prefer reversible, incremental commits.
5. Run CI after each meaningful change.
6. Preserve existing application capabilities while fixing security and wiring gaps.

## Next work order

1. Run/inspect CI for the new live-control tests.
2. Wire `request_policy` into the exchange-connect and HFT simulation routes with the smallest possible changes.
3. Add route-level regression tests for anonymous and LIVE-mode requests.
4. Wire `live_controls` through authenticated admin API/UI and the execution gateway.
5. Run CI and inspect failures.
6. Run template designer/request mapper and review suspicious/orphaned API calls.
7. Continue page-by-page functional audit and update status.