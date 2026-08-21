# CMS-my — Function / Route Map

Baseline: `main` @ `1b7fdd643ffd01e3da9f3ebc6682859568c76215`

## Global execution chain

`Template/UI → browser event/form → FastAPI route → auth/CSRF/risk gate → service/domain module → DB or public exchange/private exchange → response/redirect → template/JS update → regression test`

## Page map

| Page | Backend route | Template | Main dependencies | State/output |
|---|---|---|---|---|
| Home | `GET /`, `GET /home` | `templates/index.html` | session | landing/authenticated navigation |
| Login | `GET/POST /login` | `templates/login.html` | CMSEngine/password migration, OAuth context | session or error page |
| Dev admin | `POST /login/dev-admin-bypass` | login | CMSEngine | admin session in development |
| Register | `GET/POST /register` | `templates/register.html` | CMSEngine | user + session |
| Forgot password | `GET/POST /forgot-password` | `templates/forgot_password.html` | currently message-only | no real reset flow |
| Dashboard | `GET/POST /dashboard` | `templates/dashboard.html` | wallet, memory, session theme | wallet/memory/message |
| Settings | `GET/POST /settings` | `templates/settings.html` | session theme, user role | theme/settings |
| Marketplace | `GET/POST /marketplace` | `templates/marketplace.html` | StrategyManager, strategy performance, wallet, CCXT, plugins | exchange/wallet/Telegram/plugin UI |
| Bot | `GET/POST /bot-management` | `templates/bot_management.html` | HFTBot, StrategyManager, trades | bot state/config/history |
| Wallet | `GET/POST /wallet` | `templates/wallet.html` | Wallet, CMSC payment placeholder | credits/payment message |
| Admin | `GET/POST /admin` | `templates/admin.html` | users/plugins/wallets/risk/site settings/payout settings | admin dashboard |

## Main API map

### Authentication / identity
- `GET /auth/{provider}` → OAuth redirect; state stored in session.
- `GET /auth/{provider}/callback` → token exchange + profile lookup + user creation/login.
- `GET /auth/telegram/callback` → Telegram signature verification + session login.
- `POST /login` → `CMSEngine.secure_login` → session.
- `POST /register` → `CMSEngine.create_user` → session.
- `GET /logout` → session clear.

### Marketplace / wallet
- `POST /marketplace` action `buy_plugin` → `CMSEngine.purchase_plugin`.
- `POST /marketplace` action `connect_exchange` → direct CCXT connection → masked key stored in Wallet.
- `POST /marketplace` action `connect_wallet` → Wallet fields stored.
- `POST /marketplace` action `connect_telegram` → username stored; UI token field is ignored.
- `POST /api/strategies/activate` → plugin lookup → performance lookup → UserPlugin activation → in-memory strategy config.
- `GET/POST /wallet` → CMSC purchase placeholder; no payment settlement.

### Trading / strategy
- `POST /api/trading/test` → auth → RiskManager → StrategyManager → HFTBot.simulate → LearningMemory → Trade → risk record → JSON.
- `POST /api/trading/manual` → auth → local fee calculation → Trade/audit → JSON `executed`; **no exchange order**.
- `GET /api/trading/history` → auth → Trade list.
- `POST /api/strategy/execute` → auth → RiskManager → StrategyManager → risk record/audit/stat → JSON; **no exchange order**.
- `GET /api/strategies` → auth → strategy performance → catalog JSON.
- `POST /api/strategies/activate` → auth → plugin/access → in-memory config.

### Market data
- `GET /api/market/data` → auth → public CCXT ticker + order book + `refresh_candles` → SQLite market DB → JSON.
- `GET /api/market/history` → auth → public CCXT OHLCV → SQLite → JSON.
- `GET /api/market/news` → auth → CoinDesk RSS → SQLite → keyword sentiment → JSON.
- `GET /api/market/signal` → auth → `_market_signal` → public CCXT history → StrategyManager → JSON.

### Bot / HFT
- `GET /api/trading/status` → auth → HFTBot.status.
- `POST /api/bot/start` → admin → RiskManager kill switch → HFTBot.start → audit/stat.
- `POST /api/bot/stop` → admin → HFTBot.stop → audit/stat.
- `GET /api/bot/status` → auth → HFTBot.status.
- `POST /api/bot/backtest` → auth → public daily OHLCV → strategy evaluation → JSON.
- `POST /api/bot/simulate` → **NO AUTH** → `CMSProductionHFTBot.trade_loop` → process-local capital/history → JSON.
- `GET /api/bot/brain` → admin → process-local AI memory summary.
- `GET /api/metrics` → admin → bot/brain/strategy/risk state.

### Risk
- `GET /api/risk/status` → auth → RiskManager.status.
- `POST /api/risk/kill-switch` → admin → RiskManager.kill_switch only.

### Reporting
- `GET /api/report` → admin → reads `ADVANCED_TEST_REPORT.md` → JSON.

### Exchange
- `POST /api/user/connect-exchange` → **NO AUTH** → direct CCXT client → `load_markets()` → audit/stat → JSON.
- `backend/exchange_service.py` separately provides authenticated client management, balance, ticker, fee, minimum-order, create-order and cancel-order methods. It is not the main connection route.

## Admin router (`backend/admin.py`, prefix `/api/admin`)

- `GET /live-controls` → admin + session CSRF issuance → LiveControlState snapshot.
- `POST /live-controls/global` → admin + CSRF → global kill switch.
- `POST /live-controls/bots/{bot_id}` → admin + CSRF → bot LIVE switch.
- `POST /live-controls/ai-bots/{ai_bot_id}` → admin + CSRF → AI-bot LIVE switch.
- `GET /live-controls/audit` → admin → process-local control audit.
- `POST /users` → admin → create user.
- `POST /login` → admin credential login → session.
- `POST /plugins` → admin → create plugin.
- `GET /plugins` → admin → list plugins.
- `POST /ai-shadow/evaluate` → admin + non-LIVE mode → AIShadowTrader.evaluate.
- `POST /ai-shadow/settle` → admin + non-LIVE mode → AIShadowTrader.settle.
- `POST /ai-shadow/monitor` → admin + non-LIVE mode → AIShadowTrader.monitor.
- `POST /ai-shadow/feed/start` → admin + non-LIVE mode → AIShadowMarketFeed.start.
- `POST /ai-shadow/feed/stop` → admin + non-LIVE mode → feed.stop.
- `GET /ai-shadow/feed/status` → admin + non-LIVE mode → feed.status.

## Core domain map

### `CMSEngine`
Models: User, Plugin, UserPlugin, LearningMemory, BotStat, AuditLog, Wallet, Trade, SiteSetting.

Key transitions:
- user create/login → User
- plugin create/update/delete → Plugin/UserPlugin
- purchase → UserPlugin access window
- activation → UserPlugin.active
- strategy_test / chat / shadow events → LearningMemory
- trades → Trade
- wallet/exchange/wallet/Telegram metadata → Wallet
- site configuration → SiteSetting
- operational events → AuditLog/BotStat

### `StrategyManager`
`load_config → current_strategy → validate numeric inputs/leverage/fee → DailyCompoundHarvesterModule → gross balance → fee → net balance/PnL → response`.

Implemented strategy branches: `pure_harvester`, `high_frequency_momentum`, `compound_defender`.
Unknown names silently use `process_tick`.

### `RiskManager`
`decide(balance, leverage, stop_loss_pct) → kill switch → numeric validation → daily loss → drawdown → stop loss → position_fraction`.
`record(pnl,balance)` updates process-local daily PnL/peak.

### `ExchangeService`
`connect → authenticated CCXT client in memory → sandbox optional → load_markets → fetch_balance → process-local client registry`.
`create_order/cancel_order → execution_gateway → execution_policy + live controls → exchange executor`.

### `AIShadowTrader`
`evaluate → StrategyManager → RiskManager → AI confidence cutoff → virtual Trade(open) → audit/stat/memory`.
`monitor → find open shadow trades → SL/TP hit detection → settle`.
`settle → calculate PnL → mark Trade settled → audit/stat/memory`.

### `AIShadowMarketFeed`
`start → assert non-LIVE → public CCXT ticker loop → AIShadowTrader.monitor → virtual settlement only`.
It never calls private exchange order methods.

## Template → endpoint contract hotspots

1. Marketplace activate button → `/api/strategies/activate` works syntactically but strategy persistence/executable-strategy contract is incomplete.
2. Marketplace exchange form → browser POST `/marketplace`, separate from `/api/user/connect-exchange`.
3. Legacy `frontend/index.html` → `/api/user/connect-exchange` directly.
4. Bot simulation tests → `/api/bot/simulate` expect 401, but route currently has no auth.
5. Admin live controls → `/api/admin/live-controls/*` include CSRF contract.
6. Base template → `/static/*` resolves to `frontend/`, not root `static/`.
7. Root template references `user_name`, but route does not supply it.

## Missing/false contracts to test

- health router mounted into app;
- every protected API returns 401 anonymously;
- every browser state-changing POST has CSRF protection;
- virtual endpoints reject explicit LIVE mode;
- manual trade wording matches actual execution mode;
- plugin purchase changes balance only after a real payment/ledger contract exists;
- selected strategy persists across restart;
- activated strategy is actually executable;
- Telegram token field and backend contract agree;
- public market endpoints are rate-limited and safe-error wrapped;
- active frontend asset tree is the only authoritative asset tree.
