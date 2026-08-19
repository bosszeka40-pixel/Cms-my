# Current Work

## Active branch
`main`

## Current function
**Wallet — CMSC Exchange quote and payment intent**

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
- Marketplace / Plugins — CMSC purchase path: `DONE`
- Dashboard CMSC balance display: `DONE`
- Dashboard Settings — theme: `DONE`
- Wallet CMSC Exchange: `IMPLEMENTED — TESTING`
- Do not mark DONE until the complete route is verified.
- Withdrawal remains intentionally out of scope for this branch.

## Current implementation
- CMSC has a fixed internal settlement value of `1 CMSC = 1 EUR`.
- `/api/exchange/cmsc/quote` calculates the current EUR conversion rate and applies the administrator-configured Exchange fee.
- Supported payment currencies include EUR/USD/GBP/RUB/CHF and USDT/USDC/BTC.
- `/api/exchange/cmsc/intent` creates a pending payment intent and audit record; it does not credit CMSC before real payment confirmation.
- Administrator API exposes the CMSC Exchange fee setting with a 0–25% validation range.
- `wallet.html` now calculates a quote in the browser and can create a pending payment intent.
- `scripts/test_cmsc_exchange.py` validates fiat/crypto quote math and unsupported-currency rejection.
- `.github/workflows/cmsc-exchange-smoke.yml` provides repeatable CI verification.

## Important business rule
Payment confirmation and actual card/crypto collection must be implemented through a real payment provider before CMSC is credited. A quote or intent alone must never increase the user's CMSC balance.

## Cleanup rule
If code looks unused: mark candidate → search all references → run relevant tests → move if it belongs elsewhere → otherwise delete.

## Recovery
If chat history is lost, read `CMS_WORK/TREE.md` and this file first, then continue from the active branch.
