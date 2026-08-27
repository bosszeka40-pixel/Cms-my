# CMS-my — CURRENT FUNCTION MAP 2026-08-27

## Contract
A function is complete only when: `UI -> JS/form -> route -> auth/role -> CSRF -> rate limit -> mode -> risk -> service -> DB/external -> response -> UI state -> tests -> HTTP smoke -> deployment`.

## Existing route families
- Identity: `/login`, `/register`, `/logout`, `/forgot-password`, OAuth callbacks, Telegram callback.
- Pages: `/`, `/home`, `/dashboard`, `/settings`, `/marketplace`, `/bot-management`, `/wallet`, `/admin`.
- Market: `/api/market/data`, `/api/market/history`, `/api/market/news`, `/api/market/signal`.
- Strategy: `/api/strategies`, `/api/strategies/activate`, `/api/strategy/execute`.
- Trading: `/api/trading/test`, `/api/trading/manual`, `/api/trading/history`.
- Bot: `/api/trading/status`, `/api/bot/start`, `/api/bot/stop`, `/api/bot/status`, `/api/bot/backtest`, `/api/bot/simulate`, `/api/bot/brain`, `/api/metrics`.
- Risk: `/api/risk/status`, `/api/risk/kill-switch`.
- Exchange: `/api/user/connect-exchange` compatibility path plus ExchangeService private connection/order/cancel functions.
- Admin: live controls and AI Shadow evaluate/monitor/feed plus user/plugin/site/wallet/risk management.

## Existing domain functions
`CMSEngine` owns persistent user/plugin/access/memory/stat/audit/wallet/trade/settings transitions.
`StrategyManager` owns strategy config, validation and domain execution.
`RiskManager` owns risk decisions and loss/drawdown controls.
`HFTBot` owns current simulation/state facade; `CMSProductionHFTBot`/`AICryptoMemoryBrain` own advanced bot/AI calculations.
`AIShadowTrader` owns paper-only AI Shadow lifecycle.
`AIShadowMarketFeed` owns public market feed.
`ExchangeService` owns authenticated exchange connections and private order/cancel operations.
`ExecutionPolicy`, `LiveControlState`, `ExecutionGateway` own the LIVE safety boundary.
`market_history` owns public market/news storage.

## Existing strategy branches
Keep unchanged and executable: `pure_harvester`, `high_frequency_momentum`, `compound_defender`, existing learning-generated strategy logic. Unknown names must fail explicitly instead of silently falling back.

## Target user profile
`ProfileService -> User settings/security -> Demo toggle -> Exchange accounts -> balances -> active strategies -> bot portfolio -> CMSC wallet -> PnL/fees -> charts -> risk limits -> notifications -> audit/session history`.
Demo is a user-level default for new trading actions but every order also receives an explicit mode.

## Target bot pages
### Spot
Market/chart/orderbook, manual buy/sell, balances, open orders, trades, Grid, DCA, Rebalancing, Smart Trade and Signal Bot where supported.
### Futures/Perpetual
Long/short, leverage, isolated/cross, hedge/one-way, reduce-only, funding, mark/index, open interest, liquidation, positions/orders/risk.
### Margin
Borrow/repay, interest, margin level, liquidation risk where exchange capability supports it.
### Options
Calls/puts, strike/expiry, Greeks/IV and options orders only where supported.
### Exchange-specific
Capability-driven controls; unsupported actions hidden and server-side rejected.

## Target exchange capability map
Use `ExchangeRegistry -> ExchangeAdapter -> Capabilities -> UI schema -> ExecutionGateway`.
Capabilities: spot, margin, futures/swap, options, market/limit/stop/take-profit/OCO/trailing, reduce-only/post-only, hedge/one-way, leverage, isolated/cross, long/short, websocket/private websocket, order/trade/position streams, funding/open-interest/mark/index.
Initial adapters should cover available CCXT/API support including Binance, Bybit, OKX, KuCoin, Kraken, Coinbase, Gate.io, Bitget, MEXC, HTX, BingX, BitMart, CoinEx, Crypto.com, Deribit, Bitfinex, Gemini, WhiteBIT and Woo X, but availability must be discovered from the installed adapter layer rather than assumed.

## Target manual trading
Order flow: `create -> validate -> risk -> mode/policy -> gateway -> exchange or simulator -> lifecycle -> persist -> response -> UI`.
Lifecycle: `CREATED -> VALIDATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED`, or `CANCELED/REJECTED/ERROR`.
Never return `FILLED` without an authoritative fill result.

## Target strategy editor
Strategy schema must expose: parameters, type, min/max/default, market type, required exchange capabilities, risk profile, fee assumptions, supported modes, order types, signals, outputs and metrics. UI renders this schema dynamically.

## Target bot lifecycle
`create -> configure -> validate -> backtest -> demo/paper -> start -> heartbeat -> signal -> risk -> execution -> monitor -> pause/resume -> stop -> close/cancel -> report`.
Persist configuration, state, orders, positions, metrics, heartbeat and lifecycle events. Process memory is cache only.

## Target wallet/statistics
Wallet: CMSC balance + immutable ledger + purchases/refunds + connected exchange balances + allocation.
Statistics: equity curve, PnL, ROI, fees, drawdown, win rate, profit factor, Sharpe/Sortino, per exchange/bot/strategy and daily/weekly/monthly periods.

## Target copy trading
Separate copy-trading domain, page and permissions. Provider publishes strategy metadata/signals/performance/risk. Follower selects provider, allocation, max exposure/loss, symbols and slippage. Provider and follower balances remain separate. Signal mapping passes follower RiskManager and ExecutionGateway. No fund transfer between users.

## Target Pionex-style functional additions
Use only as product/UX reference, not copied code/assets/branding. Add Grid, DCA, Rebalancing, Smart Trade, Signal Bot, trigger price, SL/TP, profit release, bot close, AI backtesting and chart order markers while preserving current CMS visual design.

## Response contract
JSON success: `{ok:true,data,...,request_id}`. Error: `{ok:false,code,detail,request_id}`. HTML uses TemplateResponse/RedirectResponse and explicit user-facing messages. Provider stack traces and secrets never leave backend.

## Security invariant
AI, UI, bot or exchange adapters may not bypass: `Auth -> RiskManager -> ExecutionPolicy -> LiveControlState -> ExecutionGateway -> ExchangeAdapter -> Exchange` for LIVE.
