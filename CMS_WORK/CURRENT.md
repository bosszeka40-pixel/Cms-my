# Current Work

## Active branch
`cleanup/security-hardening-2026-08`

## Current function
**Marketplace / Plugins**

## Full route to trace once
1. UI/template
2. JavaScript/event handlers
3. API endpoint
4. Router/controller
5. Service/domain logic
6. Database/storage
7. External integration if applicable
8. Response/error handling
9. UI state/update
10. Integration/regression test
11. Design consistency

## Status
- Overall: `IN PROGRESS`
- Do not mark DONE until the complete route is verified.
- Do not start the next function until this branch is closed.

## Cleanup rule
If code looks unused: mark candidate → search all references → run relevant tests → move if it belongs elsewhere → otherwise delete.

## Recovery
If chat history is lost, read `CMS_WORK/TREE.md` and this file first, then continue from the active branch.
