# Final CMS Construction Plan

This document is the single production-readiness contract for Cms-my. It is additive: existing functionality must be preserved, and planned functionality that is missing or partial must be restored rather than removed.

## Operating rule

For every feature use the chain:

`feature -> route/API -> service/domain logic -> data/storage -> permissions -> UI/template -> tests -> CI`

A feature is not complete merely because a route or class exists.

## Status vocabulary

- WORKING — implemented, reachable from the intended UI/API, and covered by tests.
- PARTIAL — implementation exists but a required layer is missing or incomplete.
- MISSING — specified/expected functionality has no usable implementation.
- BROKEN — implementation exists but fails its intended contract.
- SECURITY-RISK — implementation creates an unsafe boundary, even if it appears functional.

Priorities: P0 = blocker/security/integrity; P1 = required product functionality; P2 = production polish/optimization.

## P0 — Security and execution integrity

- [ ] Request/session authentication on every user-sensitive API.
- [ ] Admin/RBAC enforcement on every administrative mutation.
- [ ] Safe error responses; no exchange credentials, stack traces, tokens, or raw exception internals in HTTP responses.
- [ ] Input validation and bounded values for every trading/financial payload.
- [ ] Central execution gateway remains the only path to real order/cancel execution.
- [ ] No direct CCXT/private order or cancel calls bypass the gateway.
- [ ] Environment gate + explicit administrative LIVE state + bot identity are all required for live execution.
- [ ] Missing or invalid live state fails closed.
- [ ] Live Trading switch is OFF by default and remains OFF after restart/deploy/configuration errors.
- [ ] Kill switch and risk gate are enforced before any execution-capable operation.
- [ ] Simulation/paper/shadow execution cannot reach real exchange order APIs.
- [ ] Exchange credentials are never persisted or returned in plaintext unless an explicitly secured storage contract exists.
- [ ] Security regression tests cover every discovered boundary.

## P0 — Application integrity

- [ ] Database schema, initialization and migrations are deterministic.
- [ ] User/session state is consistent across login, logout, OAuth and admin flows.
- [ ] Existing bot, AI, memory and strategy implementations are preserved.
- [ ] Existing templates are preserved until their replacement is verified feature-for-feature.
- [ ] No route silently reports success for an operation that did not happen.
- [ ] No production code relies on development-only bypasses.

## P1 — Complete CMS feature surface

### Core CMS

- [ ] Dashboard
- [ ] Users and profiles
- [ ] Settings
- [ ] Admin panel
- [ ] Site configuration
- [ ] Audit log
- [ ] Notifications/status surfaces

### Authentication

- [ ] Login/register
- [ ] Password recovery with a real delivery/verification workflow or an explicit configured provider
- [ ] OAuth providers
- [ ] Telegram authentication where configured
- [ ] Session expiration and logout
- [ ] RBAC/admin authorization

### Trading intelligence

- [ ] Market ticker/order book
- [ ] Historical candles
- [ ] News and sentiment
- [ ] Signals
- [ ] Strategy catalog
- [ ] Strategy performance/backtests
- [ ] Strategy activation/deactivation
- [ ] AI brain
- [ ] Memory
- [ ] Chat

### Bot

- [ ] Bot start/stop/status
- [ ] Simulation
- [ ] Backtesting
- [ ] Bot metrics
- [ ] Brain/memory metrics
- [ ] Risk state and kill switch
- [ ] Explicit separation between simulation and live execution

### Marketplace and licensing

- [ ] Marketplace catalog
- [ ] Plugin/strategy descriptions and pricing
- [ ] Purchases
- [ ] License durations
- [ ] Activation/deactivation
- [ ] Ownership/access checks
- [ ] Subscription/licensing state
- [ ] Payment state reconciliation
- [ ] Admin purchase/license management

### Exchange and wallet integrations

- [ ] Supported exchange directory
- [ ] Public market-data clients
- [ ] Authenticated exchange connection workflow
- [ ] Credential protection and ownership binding
- [ ] Wallet providers
- [ ] Wallet connection state
- [ ] Payout configuration
- [ ] No accidental live execution through connection/setup endpoints

## P1 — Frontend/template completeness

Every template under `templates/` must be mapped to its route and backend data contract. Every backend feature intended for users/admins must have a corresponding UI entry point unless it is intentionally API-only.

Required mapping includes, at minimum: admin, dashboard, bot management, marketplace, wallet, settings, login, register, install and all feature-specific templates found during inventory.

## P1 — Quality

- [ ] Unit tests for domain logic.
- [ ] API tests for auth/RBAC and validation.
- [ ] Regression tests for security boundaries.
- [ ] Integration tests for DB/services.
- [ ] End-to-end/smoke tests for critical user flows.
- [ ] Tests for simulation/paper/shadow execution.
- [ ] Tests proving live execution is blocked by default.
- [ ] CI passes from a clean checkout.
- [ ] Submodule metadata is valid or the submodule is deliberately migrated/removed without losing its functionality.

## P2 — Production readiness

- [ ] Production configuration documented.
- [ ] Required secrets documented without exposing values.
- [ ] Secure session/cookie settings for production.
- [ ] Logging and auditability.
- [ ] Health/readiness checks.
- [ ] Deployment instructions.
- [ ] Backup/recovery expectations.
- [ ] Dependency/update policy.
- [ ] Documentation matches actual behavior.
- [ ] No known P0/P1 defects remain.

## Definition of Done

The CMS is ready for production only when all intended functions are reachable through their correct UI/API, their data and permission contracts are valid, critical paths are tested, CI is green, security boundaries are verified, and no P0/P1 defect remains.

Live trading is intentionally excluded from development/test execution. The live code path may be production-ready, but real order submission remains explicitly OFF until a separate, deliberate operational activation is performed by the authorized operator.
