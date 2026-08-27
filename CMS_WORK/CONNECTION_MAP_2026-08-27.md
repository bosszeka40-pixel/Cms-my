# CMS-my — CURRENT CONNECTION / LOGIC MAP 2026-08-27

## Global graph
```text
Browser/Jinja/JS
 -> FastAPI route
 -> Auth/Role
 -> CSRF + Rate Limit
 -> Mode + Risk
 -> Controller/Service
 -> Domain
 -> DB / public API / private exchange
 -> Stable response
 -> UI state
 -> audit/statistics
```

## User/account graph
```text
Register/Login/OAuth/Telegram
 -> User/session
 -> Profile
 -> Demo default + security + notifications
 -> Exchange Accounts
 -> Wallet/CMSC ledger
 -> Bots/Strategies
 -> Statistics/Audit
```

## Exchange graph
```text
Exchange settings
 -> ExchangeRegistry
 -> ExchangeAdapter
 -> validate credentials
 -> sandbox/testnet
 -> discover capabilities
 -> load markets
 -> fetch balances
 -> persist encrypted credential reference + account metadata
```
Secrets are never returned to frontend, logged, stored in localStorage, or sent to AI.

## Market graph
```text
ExchangeAdapter public API / websocket
 -> ticker/orderbook/OHLCV/trades/funding/mark/index/OI
 -> MarketDataService
 -> cache + market history DB
 -> chart/orderbook/watchlist/signals
```
Slow public calls must be cached/rate limited; websocket disconnect falls back safely where possible.

## Strategy graph
```text
Market data + user parameters
 -> Strategy schema validation
 -> StrategyManager
 -> selected strategy branch
 -> signal/order intent
 -> RiskManager
 -> mode/policy
 -> simulator or ExecutionGateway
```
Existing strategies remain. No unknown strategy fallback.

## Manual trading graph
```text
UI order ticket
 -> order schema
 -> auth + CSRF
 -> exchange capability validation
 -> risk
 -> DEMO/PAPER/BACKTEST/SHADOW/LIVE mode
 -> simulator OR ExecutionGateway
 -> exchange adapter
 -> order lifecycle
 -> Trade/Order persistence
 -> UI + audit
```

## LIVE safety graph
```text
User/Bot/Copy/AI intent
 -> Auth
 -> RiskManager
 -> ExecutionPolicy
 -> Global + bot live controls
 -> ExecutionGateway
 -> ExchangeAdapter
 -> private exchange API
```
No alternate private-order path is allowed.

## Bot graph
```text
Bot config
 -> strategy parameters
 -> backtest
 -> demo/paper
 -> runtime worker
 -> market stream
 -> strategy signal
 -> risk
 -> execution
 -> order/position updates
 -> PnL/fees/equity
 -> heartbeat/persistence
 -> pause/resume/stop/emergency
```
Runtime state may be cached in memory but authoritative state is persistent.

## Copy trading graph
```text
Provider strategy
 -> normalized signal
 -> copy policy
 -> follower allocation/limits
 -> follower RiskManager
 -> follower mode
 -> ExecutionGateway
 -> follower exchange account
 -> independent order/trade/PnL
```
Provider and follower balances are never combined.

## Wallet/statistics graph
```text
Exchange balances + CMSC ledger + trades + fees
 -> accounting service
 -> equity/PnL/ROI/drawdown/win-rate/profit-factor/Sharpe/Sortino
 -> daily/weekly/monthly
 -> per exchange/bot/strategy
 -> charts + export
```

## Pionex-style feature placement
Preserve existing visual design. Reorganize information only:
- Profile: demo mode, security, exchanges, notifications, risk defaults.
- Markets: watchlist, chart, orderbook, trades, market data.
- Spot/Futures/Margin/Options: context-specific trading terminal.
- Bots: bot portfolio + create/configure/backtest/start/pause/stop.
- Strategies: strategy catalog + parameter schema + backtest + activation.
- Copy Trading: provider/follower marketplace and independent follower risk.
- Wallet: CMSC + exchange balances + ledger + allocation.
- Statistics: performance charts and bot/strategy/exchange analytics.
- Admin: site, users, plugins, risk, live controls, audit, AI Shadow.

## Response/error graph
Every API returns stable JSON. Success: `ok=true`, `data`, `request_id`. Error: `ok=false`, stable `code`, safe `detail`, `request_id`. UI must update from returned authoritative state rather than optimistic claims for fills/balances.

## Persistence graph
Core persistent state: users, plugins/access, memory, wallet, CMSC ledger, trades/orders, strategy configs, bot configs, exchange accounts metadata, stats, audit.
Market persistent state: candles/news/market snapshots as appropriate.
Runtime-only: websocket handles, caches, workers, ephemeral locks. Runtime-only data must never be the sole source of truth for account balances or orders.

## Deployment graph
Codespace/local -> `backend.main:app` on port 8000.
Netlify -> `netlify/functions/api.py` -> Mangum -> FastAPI; writable serverless paths use `/tmp` only and must not be treated as durable production storage.
Docker/PaaS -> process server -> health/readiness HTTP routes.

## Verification matrix
For each connection test both positive and negative paths: unauthorized, wrong role, CSRF failure, unsupported capability, invalid mode, risk block, exchange rejection, network timeout, duplicate request, restart/reconnect, partial fill and final fill/cancel.
