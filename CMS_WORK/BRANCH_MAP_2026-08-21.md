# CMS-my — Complete Branch Map / Strict Audit

Date: 2026-08-21
Baseline: current `main` at audit start `1b7fdd643ffd01e3da9f3ebc6682859568c76215`.

## Scope
The repository currently exposes **34 branches total: 33 non-main branches + `main`**. This is the authoritative inventory captured during this audit. A branch relation is not a quality score. Diverged/behind branches are reference material and must not be merged wholesale.

## Branch inventory

| Branch | Role / observed purpose | Audit handling |
|---|---|---|
| `main` | Integration baseline | Primary audit target; RED until gates pass |
| `audit/strict-2026-08-21` | Audit work | Reference audit state |
| `backup/2026-08-19-all-work` | Full historical backup | Rollback/reference only |
| `backup/2026-08-19-work-state` | Work-state backup | Rollback/reference only |
| `chore/mece-opencode-setup` | Process/tooling | Inspect selectively |
| `ci/real-cms-smoke` | CI smoke experiment | Inspect selectively |
| `cleanup/cmsc-exchange-security-final` | CMSC/exchange/security | High-value selective source |
| `cleanup/security-hardening-2026-08` | Security hardening | Historical/security reference |
| `codespace-special-zebra-r7r9pp46qw6xhwwqx` | Codespace experiment | Historical reference |
| `codex/-github` | Codex/GitHub work | Historical reference |
| `codex/final-cms-construction` | CI/exchange/production-plan work | High-value selective source |
| `dependabot/pip/email-validator-2.3.0` | Dependency candidate | Compatibility gate required |
| `dependabot/pip/pydantic-2.13.4` | Dependency candidate | High compatibility gate |
| `dependabot/pip/pyyaml-6.0.3` | Dependency candidate | Compatibility gate |
| `dependabot/pip/uvicorn-0.52.3` | Dependency candidate | Compatibility gate |
| `dependabot/pip/werkzeug-3.1.8` | Dependency candidate | Compatibility gate |
| `fix/ci-failures` | CI failure fixes | Selective reference |
| `fix/ci-runtime-2026-08-21` | CI/deploy runtime | Selective reference |
| `fix/codespace-local-runtime-2026-08-21` | Codespace runtime | High-value selective source |
| `fix/netlify-python312-cmsc` | Netlify/Python/health | High-value selective source |
| `fix/sandbox-smoke-suite` | Sandbox tests | Historical reference |
| `fix/sandbox-smoke-suite-v2` | Sandbox tests | Historical reference |
| `fix/sandbox-smoke-suite-v3` | Sandbox tests | Historical reference |
| `fix/sandbox-smoke-suite-v4` | CMSC/sandbox/security | Selective source |
| `fix/sqlite-ci-runtime` | SQLite/CI runtime | High-value selective source |
| `integrate-main-fixes-safe` | Integration experiment | Historical reference |
| `restore/working-runtime-2026-08-20` | Working runtime restoration | Rollback/reference; do not wholesale merge |
| `rollback-before-full-5b0b93c` | Rollback checkpoint | Preserve |
| `rollback-before-full-5b0b93c-2026-08-19` | Rollback checkpoint | Preserve |
| `temp-full-5b0b93c` | Temporary integration | Historical reference |
| `v0/ci-failure-investigation-d211849a` | CI investigation | Historical reference |
| `work/connect-exchange-security` | Exchange/security work | Selective source |
| `work/connect-exchange-security-ci` | Exchange/security + CI | Selective source |
| `work/connect-exchange-security-ci2` | Later exchange/security + CI | Selective source |

## Branch dependency strategy

1. **Never** merge a divergent branch wholesale merely because it has a desirable commit.
2. For every candidate change: compare commit → inspect changed files → trace imports/callers/templates/tests → transfer the minimum safe unit → run regression tests.
3. Keep rollback branches intact until the release baseline is independently proven.
4. Treat `main` as the integration line, not automatically as the most correct historical implementation.

## High-value historical sources

The most important recovery/reference branches are:
- `restore/working-runtime-2026-08-20`
- `fix/codespace-local-runtime-2026-08-21`
- `fix/ci-runtime-2026-08-21`
- `fix/netlify-python312-cmsc`
- `fix/sqlite-ci-runtime`
- `work/connect-exchange-security-ci2`
- `cleanup/cmsc-exchange-security-final`
- `codex/final-cms-construction`

## Known branch-risk pattern

The repository has repeatedly accumulated parallel fixes for the same boundary: runtime/deployment, health checks, exchange connection, security gates, and smoke tests. The resulting graph can contain mutually incompatible assumptions. Therefore branch history is part of the audit and must be read as evidence, not as an instruction to merge everything.

## Current branch-map conclusion

**Branch topology is complex but recoverable.** No branch is approved for wholesale merge. The safe recovery unit is a traced file/function/commit with a corresponding test contract.
