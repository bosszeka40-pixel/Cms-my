# Cms-my — Audit & Work Log

Updated: 2026-08-17

## Control points

- Current working branch: `cleanup/security-hardening-2026-08`
- Latest checkpoint: `4966c9accef00ce20864c1dd40f94b65cd4d9567`
- Git commits remain the rollback mechanism; this file is the navigation/checklist.

## Done / verified

- [x] Admin Shadow endpoints require admin session.
- [x] Shadow market feed uses public market data and does not contain private order calls.
- [x] Shadow virtual trades have settlement and P/L lifecycle.
- [x] Shadow feed fails closed when `TRADING_MODE=live`.
- [x] Centralized fail-closed execution policy added in `backend/security/execution_policy.py`.
- [x] Added automated unit coverage for the execution policy: DEMO default, unknown-mode fail-closed, independent LIVE gate, and virtual/live separation.
- [x] CI compile step passes on checkpoint `ca8310b`.
- [x] CI dependency audit found missing declared dependencies (`Werkzeug`, `PyYAML`); both are now declared in `requirements.txt`.
- [x] Added static CMS request/path mapper: `tools/cms_request_mapper.py`.

## Done but requires verification

- [ ] Re-run CI after dependency fix.
- [ ] Run `python tools/cms_request_mapper.py` and inspect generated `docs/REQUEST_MAP.md`/`.json`.
- [ ] Wire execution policy directly into every private exchange execution path.
- [ ] Verify all `create_order`, `cancel_order`, and private CCXT calls.
- [ ] Verify `/api/user/connect-exchange` requires an authenticated user and does not persist raw secrets.
- [ ] Verify `/api/trading/manual` is explicitly virtual or guarded as real execution.
- [ ] Verify `/api/trading/test` cannot bypass Shadow/Demo controls.
- [ ] Verify kill-switch is enforced immediately before real execution.
- [ ] Verify CSRF protection on state-changing browser routes.
- [ ] Verify rate limits on authentication and trading endpoints.

## Authentication / installation

- [ ] Implement `/install` first-run setup.
- [ ] Create initial admin securely during installation.
- [ ] Generate/require a strong `SECRET_KEY`.
- [ ] Disable and remove `DEV_ADMIN_BYPASS` before production release.
- [ ] Lock `/install` after successful initialization.

## AI / trading pipeline

- [x] Strategy → Shadow decision skeleton exists.
- [x] RiskManager participates in Shadow decision.
- [x] Virtual position and settlement exist.
- [ ] Replace externally supplied AI confidence with actual AI analysis service.
- [ ] Connect live ticker/candle stream to new Shadow decisions, not only settlement.
- [ ] Persist learning results and verify training inputs.
- [ ] Add Shadow performance metrics and error telemetry.

## Request / execution audit

- [x] Static request/path mapper added.
- [ ] Generate and inspect the full request map.
- [ ] Trace all application calls that can reach an exchange.
- [ ] Separate public market-data calls from private authenticated calls.
- [ ] Prove DEMO/SHADOW cannot reach private order methods.
- [ ] Record request metadata without API keys, secrets, or authorization headers.
- [ ] Test kill-switch and execution gate immediately before order submission.

## Legacy cleanup — DO NOT DELETE YET

- [ ] Identify duplicate/obsolete `main` files.
- [ ] Identify legacy databases and confirm active DB path.
- [ ] Identify unused modules/imports.
- [ ] Identify obsolete trading endpoints.
- [ ] Verify templates and terminal chart dependencies.
- [ ] Delete only after dependency scan and successful CI.

## Final gate before LIVE

- [ ] Full security audit.
- [ ] Full trading-flow audit.
- [ ] Sandbox run with request tracing.
- [ ] Negative tests proving DEMO/SHADOW cannot create real orders.
- [ ] Kill-switch test.
- [ ] Credential leakage test.
- [ ] CI green.
- [ ] Explicit manual approval required to enable LIVE gate.
