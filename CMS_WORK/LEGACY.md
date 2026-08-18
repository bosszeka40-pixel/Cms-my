# Legacy Cleanup

Only confirmed leftovers belong here.

## Candidates
- `HFTSimulatePayload` / `/api/bot/simulate` — VERIFY references before isolation/removal.
- Inline exchange connection in `/marketplace` — VERIFY against `backend/exchange_service.py`.
- `DEV_ADMIN_BYPASS` — keep until installer/admin flow is replaced and verified.
- `forgot_password_submit` — VERIFY actual dependency.
- `archive/` — LEGACY; do not delete until references are checked.

## Rule
A candidate is removed only after all references, tests, and entry points are checked.
