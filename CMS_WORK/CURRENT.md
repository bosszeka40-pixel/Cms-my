# Current Work

## Active branch
`cleanup/security-hardening-2026-08`

## Current function
**Marketplace / Plugins — CMSC purchase path**

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
- Deployment smoke: `DONE`
- CMSC marketplace purchase billing: `IMPLEMENTED — TESTING`
- Do not mark DONE until the complete route is verified.
- Do not start the next function until this branch is closed.

## Current implementation
- Paid plugin purchases are routed from the marketplace UI to `/api/strategies/purchase`.
- CMSC is the internal settlement unit at a fixed `1 CMSC = 1 EUR`.
- Paid purchases debit CMSC and create/extend plugin access in one transaction.
- Insufficient CMSC rejects the purchase.
- Free strategies do not debit CMSC.
- Purchase audit entries are written to `audit_logs`.

## Cleanup rule
If code looks unused: mark candidate → search all references → run relevant tests → move if it belongs elsewhere → otherwise delete.

## Recovery
If chat history is lost, read `CMS_WORK/TREE.md` and this file first, then continue from the active branch.
