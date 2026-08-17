# CMS-my — UI / Function Audit

## Goal
Restore the original CMS concept before making cosmetic redesigns. Existing functionality is preserved unless it is demonstrably wrong, unsafe, or unused.

## Current findings

### Global layout (`templates/base.html`)
- Header/navigation covers Home, Dashboard, Wallet, Marketplace, Bot, Settings, Admin, Login/Register and theme switching.
- Trading-specific JS/CSS is currently loaded globally. **TODO:** scope these assets to the trading page to reduce coupling.
- Theme switching is implemented as a POST to dashboard. **TODO:** add CSRF protection before hardening this flow.

### Dashboard
Present:
- CMSC balance and connected services summary.
- Theme settings.
- AI assistant chat.
- Marketplace/bot shortcuts.
- Strategy-memory statistics table/chart.

Needs audit:
- `/api/chat` authorization and error handling.
- Memory chart sizing/DPR/responsive behavior.
- Verify all displayed wallet fields match current model semantics.
- Restore any original dashboard widgets that existed before Gemini changes.

### Wallet
Present:
- CMSC balance.
- Provider/exchange/Telegram status.
- CMSC purchase form.
- Referral information.

Needs audit:
- Purchase flow and payment backend must match displayed claims.
- Referral code must not expose or derive sensitive account information.
- Verify supported payment currencies and actual payment implementation.

### Marketplace
Present:
- Exchange connection.
- Wallet connection.
- Telegram connection.
- Plugin catalog, purchase, activation and purchase history.

Needs audit:
- Exchange credentials must never be displayed or logged in plaintext.
- `/api/strategies/activate` authorization and CSRF.
- Plugin pricing/ownership/access dates must match backend.
- Separate paid products from simulated strategy performance claims.

### Trading / Bot terminal
Present:
- Pair/exchange/timeframe selection.
- Market ticker/history.
- Candlestick canvas.
- Order book.
- Manual simulation.
- News/sentiment.
- Risk status / kill switch display.
- Bot start/stop.
- Strategy selection.
- Strategy test.
- Balance chart.
- Trade history.
- Backtest.
- New live 1-second renderer and Binance trade-stream path.

Known issues / corrections:
- Historical API currently returns candle objects `{timestamp, open, high, low, close, volume}` while legacy frontend code expects array rows. Normalize this at one boundary; do not keep two incompatible formats.
- `LIVE 1s` must distinguish true trade-stream aggregation from ticker fallback.
- Trading modes must be visually and functionally separated: SIMULATION / PAPER / LIVE.
- Real-order controls must require explicit live mode and confirmation.
- Live 1-second display is not a promise of one-second order execution latency.

Target terminal UX:
- Professional exchange-style layout.
- Pair/price/24h summary.
- 1s, 5s, 15s, 30s, 1m, 5m, 15m, 30m, 1h, 4h, 1D.
- Candles + volume + crosshair + OHLC + zoom/pan.
- Order book + recent trades.
- Orders / positions / history tabs.
- P&L, margin, fees, risk and kill switch.
- Stop-loss / take-profit.
- Responsive/mobile layout.

### Settings
Present:
- Profile information.
- Theme.
- Links to CMS sections.

Needs audit:
- Settings page is currently minimal compared with the rest of the CMS. Determine which original account/security/bot settings are missing.
- Add password/security settings only after the password migration path is verified.

### Admin
Present:
- Site settings.
- Social login status.
- Payout settings.
- Trading defaults.
- Risk / kill switch.
- Plugin management.
- User roles.
- Wallets.
- Purchases.
- Platform statistics.
- Diagnostics.

Needs audit:
- Verify every form action maps to a current backend action.
- Role changes need CSRF and authorization regression tests.
- Kill switch must fail safe and be auditable.
- Payout settings are high-impact and require strict authorization/validation.

### Authentication
Present:
- Login/register/social-login structure.
- Temporary DEV admin bypass.
- Password compatibility layer has been added.
- Installer service exists but HTTP `/install` is not yet connected.

Required:
- `/install` must create the first admin using the existing user model/database.
- After installation, `/install` must be inaccessible.
- Production must never rely on DEV bypass.
- Login rate limiting + CSRF + secure cookies + password migration tests.

## Priority order
1. Map every template to its backend route/API.
2. Normalize market candle data and verify historical renderer.
3. Verify live 1s trade aggregation.
4. Audit missing/broken functions page-by-page.
5. Restore original intended functionality before cosmetic redesign.
6. Redesign trading terminal UX without removing capabilities.
7. Security hardening and regression tests.
8. Full CI/browser smoke test before merge.

## Rule
Do not remove an existing UI element or backend capability merely because it looks redundant. First prove that it is legacy, broken, duplicated, or contrary to the intended CMS design and record the decision here and in `PROJECT_STATUS.md`.
