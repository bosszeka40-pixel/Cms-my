# Cell: cms-functionality

## Scope
Read-only audit of intended CMS/template functionality versus what is actually implemented.

## Task
Inspect routes/pages/components/services/configuration and identify missing, stubbed, disabled, inconsistent, or partially implemented CMS features. Pay special attention to functions that the site template appears to require but that are absent or incomplete.

## Constraints
- Do not edit production code.
- Do not invent requirements; distinguish observed behavior from inferred intent.

## Report
Create `.mece/cells/cms-functionality/REPORT.md` with a feature matrix: implemented / partial / missing / unclear, evidence paths, dependencies, and recommended next implementation cells. Include session id if available.
