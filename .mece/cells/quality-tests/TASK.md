# Cell: quality-tests

## Scope
Read-only verification and test-quality audit.

## Task
Inspect package/tooling configuration, test suites, lint/typecheck/build scripts, CI workflows, and reproducibility. Determine which checks can be run locally and identify missing coverage or failing checks.

## Constraints
- Do not edit production code or CI configuration in this audit wave.
- Do not install unreviewed dependencies.

## Report
Create `.mece/cells/quality-tests/REPORT.md` with available commands, observed results, coverage gaps, blockers, and recommended verification gates for the next wave. Include session id if available.
