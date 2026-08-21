# CMS-my — Branch Map

Baseline: `main` @ `1b7fdd643ffd01e3da9f3ebc6682859568c76215`

Status notation: `ahead/behind` is commit distance from main; it is not a quality score. Diverged branches must never be merged wholesale without file-level review.

## All branches

| Branch | Relation to main | Audit conclusion |
|---|---|---|
| `main` | HEAD `1b7fdd6` | Current integration baseline; RED until strict audit gates pass |
| `backup/2026-08-19-all-work` | behind 183 | Historical rollback only |
| `backup/2026-08-19-work-state` | behind 183 | Historical rollback only |
| `chore/mece-opencode-setup` | diverged +5 / -259 | Process/documentation only; do not merge wholesale |
| `ci/real-cms-smoke` | behind 249 | Historical CI experiment |
| `cleanup/cmsc-exchange-security-final` | diverged +7 / -90 | Contains CMSC/security work; inspect selectively |
| `cleanup/security-hardening-2026-08` | behind 90 | Older security branch; main contains newer descendants |
| `codespace-special-zebra-r7r9pp46qw6xhwwqx` | behind 276 | Old Codespace experiment |
| `codex/-github` | behind 258 | Historical Codex work |
| `codex/final-cms-construction` | diverged +6 / -259 | Contains CI/exchange/production-plan changes; inspect selectively |
| `dependabot/pip/email-validator-2.3.0` | diverged +1 / -4 | Dependency update candidate; test compatibility before merge |
| `dependabot/pip/pydantic-2.13.4` | diverged +1 / -4 | Dependency update candidate; high compatibility risk |
| `dependabot/pip/pyyaml-6.0.3` | diverged +1 / -1 | Dependency update candidate |
| `dependabot/pip/uvicorn-0.52.3` | diverged +1 / -4 | Dependency update candidate |
| `dependabot/pip/werkzeug-3.1.8` | diverged +1 / -2 | Dependency update candidate |
| `fix/ci-runtime-2026-08-21` | diverged +2 / -90 | CI/deploy fixes; inspect file-level |
| `fix/codespace-local-runtime-2026-08-21` | diverged +4 / -2 | **Important** Codespace fixes; compare selectively with main |
| `fix/netlify-python312-cmsc` | diverged +2 / -193 | Python/health/Netlify fixes; inspect selectively |
| `fix/sandbox-smoke-suite` | behind 186 | Historical sandbox suite |
| `fix/sandbox-smoke-suite-v2` | behind 186 | Historical sandbox suite |
| `fix/sandbox-smoke-suite-v3` | behind 186 | Historical sandbox suite |
| `fix/sandbox-smoke-suite-v4` | diverged +6 / -186 | CMSC smoke/security changes; inspect selectively |
| `fix/sqlite-ci-runtime` | diverged +2 / -191 | SQLite/CI fixes; inspect selectively |
| `integrate-main-fixes-safe` | behind 98 | Historical integration branch |
| `restore/working-runtime-2026-08-20` | behind 3 | Near-main historical runtime restore; useful rollback/reference |
| `rollback-before-full-5b0b93c` | behind 99 | Rollback checkpoint |
| `rollback-before-full-5b0b93c-2026-08-19` | behind 99 | Rollback checkpoint |
| `temp-full-5b0b93c` | behind 258 | Historical temporary integration |
| `work/connect-exchange-security` | diverged +16 / -90 | Large exchange/CMSC security work; inspect selectively |
| `work/connect-exchange-security-ci` | diverged +7 / -90 | Exchange/CMSC security + CI |
| `work/connect-exchange-security-ci2` | diverged +8 / -90 | Exchange/CMSC security + CI, later iteration |

## Important branch observations

1. `main` is not the oldest branch; it is the newest integration line in this audit.
2. Several branches contain unique work that is not an ancestor of main. This is why blind merging is unsafe.
3. The most relevant branches for recovery/reference are:
   - `restore/working-runtime-2026-08-20`
   - `fix/codespace-local-runtime-2026-08-21`
   - `fix/ci-runtime-2026-08-21`
   - `fix/netlify-python312-cmsc`
   - `fix/sqlite-ci-runtime`
   - `work/connect-exchange-security-ci2`
   - `cleanup/cmsc-exchange-security-final`
   - `codex/final-cms-construction`
4. Historical rollback branches must remain intact until the release baseline is proven.
5. No branch is marked safe-to-merge wholesale. The correct method is file-level/cherry-pick-level transfer with regression tests.
