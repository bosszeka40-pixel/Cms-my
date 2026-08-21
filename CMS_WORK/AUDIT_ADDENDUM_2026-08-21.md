# Strict Audit Addendum — verified after map creation

## Additional HIGH finding

### H-11 — `/api/trading/test` risk gate uses hard-coded leverage
The route calls `RiskManager.decide(payload.current_balance, 1.0)` and only afterwards calls `StrategyManager.execute(...)`, which uses the configured leverage from `backend/config.yaml`/StrategyManager.

Therefore the risk gate validates leverage `1.0`, while the actual strategy calculation can use a higher configured leverage (currently config is 1.9). The pre-trade risk check is therefore not evaluating the same leverage that the strategy uses.

Status: **OPEN / HIGH**.

## Runtime verification status

- Current `main` commit: `1b7fdd643ffd01e3da9f3ebc6682859568c76215`.
- GitHub Actions reports no workflow run for that commit through the available connector at audit time.
- Therefore this audit does **not** claim the current main runtime is passing CI.
- The audit is source/config/test-contract based unless a finding explicitly says it was reproduced by an existing test contract or prior deployment log.

## Branch-specific high-value references

- `fix/codespace-local-runtime-2026-08-21`: +4/-2 versus main; changes `.devcontainer/devcontainer.json`, `.vscode/tasks.json`, `scripts/codespace-start.sh`, and requirements. Review selectively because this is directly related to the user's Codespace failure.
- `fix/ci-runtime-2026-08-21`: +2/-90; changes CI/deploy smoke configuration. Review selectively.
- `fix/netlify-python312-cmsc`: +2/-193; changes `.python-version` and `backend/health.py`. Review selectively.
- `work/connect-exchange-security`: +16/-90; contains CMSC/payment/exchange/rate-limit/security work. Review file-by-file.
- `work/connect-exchange-security-ci2`: +8/-90; later CI/security iteration of that line.
- `cleanup/cmsc-exchange-security-final`: +7/-90; CMSC/exchange security work plus tests.
- `codex/final-cms-construction`: +6/-259; adds CI/exchange/production-plan/test material.

## Rule for tomorrow

Do not merge these branches wholesale. For each desired fix, compare the exact file against main, trace its imports/callers/tests, and transfer only the compatible change. Then run the full regression suite and real HTTP smoke.
