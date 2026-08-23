# Cell: security

## Scope
Read-only security audit of the CMS.

## Task
Inspect authentication/authorization, secrets/configuration handling, API boundaries, input validation, dependencies, filesystem/process access, and any trading/bot integration. Identify vulnerabilities, unsafe defaults, and areas needing verification.

## Constraints
- Do not edit production code.
- Do not expose or copy secrets into reports.
- Treat live exchange trading as out of scope for activation; simulation-only behavior must remain explicit unless separately authorized and safely implemented.

## Report
Create `.mece/cells/security/REPORT.md` containing findings with severity, evidence/path, impact, recommended remediation, verification steps, and residual risk. Include session id if available.
