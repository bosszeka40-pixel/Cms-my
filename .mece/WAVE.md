# MECE → OpenCode wave

## Goal
Establish a safe MECE/OpenCode execution wave for the CMS. The parent conductor (ChatGPT/Codex) coordinates; OpenCode is the execution muscle.

## Rules
- Cells are mutually exclusive in ownership.
- This first wave is **audit/planning only**: no production code edits by cells.
- Each cell must write `.mece/cells/<CELL-ID>/REPORT.md` when complete.
- Findings that require implementation become follow-up cells with explicit file ownership.
- Never add secrets, private credentials, or exchange live-trading keys to the repository.

## Cells
1. `repo-state` — repository structure, current implementation state, existing tests and obvious blockers.
2. `security` — security posture and risky paths/configuration; report only.
3. `cms-functionality` — compare existing CMS/template functionality against the intended feature set; identify missing or incomplete functionality.
4. `quality-tests` — test/build/lint coverage and reproducibility; identify failures and missing checks.

## Completion
After all reports exist, the parent writes `.mece/SYNTHESIS.md` and creates the next implementation wave with non-overlapping file ownership.
