# CI failure — 2026-08-19

## Result
The CMS smoke job itself passed through application startup and readiness checks.

- Dependencies installed successfully.
- Backend compilation passed.
- Application import passed.
- Uvicorn started successfully.
- `/health` returned `{"status":"ok"}`.
- `/ready` returned `{"status":"ready"}`.

## Remaining failure
The workflow failed during `actions/checkout` post-job cleanup with git exit code 128:

`fatal: No url found for submodule path 'Cms' in .gitmodules`

The repository tree contains `Cms` as a gitlink/submodule entry (`mode 160000`) but there is no `.gitmodules` file. This is repository metadata, not a CMS runtime failure.

## Fix
Remove the stale `Cms` gitlink from the repository tree. Do not change CMS application code.
