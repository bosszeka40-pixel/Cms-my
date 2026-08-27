# CMS-my — AI CODER MASTER SPEC
## Полная карта функционала, восстановление потерянного, архитектура бота и целевой Pionex-style terminal

**Дата:** 2026-08-27  
**Репозиторий:** `bosszeka40-pixel/Cms-my`  
**Главный рабочий каталог:** `CMS_WORK/`  
**Назначение:** единая инструкция для AI Coder/Codex при восстановлении, интеграции и профессионализации CMS.

> Полная версия документа создана в текущем рабочем файле `CMS_MY_AI_CODER_MASTER_SPEC_2026-08-27.md`. В репозитории этот документ является master-spec: существующее не удалять, сначала трассировать и восстанавливать, затем расширять.

## Критические правила

1. Не переписывать CMS с нуля.
2. Не удалять существующую функциональность только потому, что она сейчас не видна в UI.
3. Сначала восстановить и проверить существующую архитектуру, затем расширять.
4. Существующие bot/AI/memory/strategy/risk/execution/security модули считать источником истины, пока dependency/caller tracing не докажет обратное.
5. DEMO, BACKTEST, SHADOW/PAPER и LIVE должны быть разными execution modes.
6. LIVE всегда проходит через единый execution gateway + policy + live controls.
7. API-ключи никогда не показывать целиком, не логировать и не отдавать frontend/LLM.
8. UI делать профессиональным trading-terminal в духе современных криптобирж и Pionex UX, но не копировать бренд, логотипы, изображения, тексты или закрытый код.
9. Сначала обеспечить boot, затем HTTP/API, затем terminal, затем exchange/bot/live path.
10. Любое расширение additive: существующая задумка бота и CMS не заменяется.

## Подтверждённый текущий функционал

### Core
- FastAPI `backend/main.py`
- Jinja2
- sessions/auth/roles
- OAuth Google/GitHub + state validation
- Telegram login + HMAC
- password auth + SHA-256 → scrypt migration
- registration/logout/password recovery
- admin router
- static frontend mount

### Data model / CMSEngine
- User
- Plugin
- UserPlugin
- LearningMemory
- BotStat
- AuditLog
- Wallet
- Trade
- SiteSetting
- user/plugin/access/memory/trade/audit/stat/wallet/settings operations

### Marketplace
- strategy/plugin catalog
- purchase/access duration
- activation
- exchange/wallet/Telegram UI
- strategy performance/catalog
- default strategies: `pure_harvester`, `high_frequency_momentum`, `compound_defender`
- rule-based `learned_adaptive_momentum` creation after the existing profitable-test condition

### Market terminal/backend
- ticker
- order book
- OHLCV/history
- SQLite market history
- news/RSS
- keyword sentiment
- market signal generation
- candle renderer
- OHLC/volume/grid/price scale/tooltip
- resize/DPR
- periodic refresh
- Binance websocket trade aggregation
- ticker fallback for other exchanges

### Strategy / Risk / Trading
- `backend/modules/strategy_manager.py`
- StrategyManager config loading/validation/execution/fees/PnL
- `pure_harvester`
- `high_frequency_momentum`
- `compound_defender`
- RiskManager kill switch/daily PnL/peak/drawdown/SL/position fraction/validation
- `/api/trading/test`
- `/api/strategy/execute`
- `/api/trading/manual`
- `/api/trading/history`
- `/api/strategies`
- `/api/strategies/activate`

### Bot / AI memory
- `backend/bot.py` HFTBot: start/stop/status/simulate/stats/events
- `backend/hft_brain.py` CMSProductionHFTBot
- `AICryptoMemoryBrain`
- persistent `LearningMemory`
- `/api/trading/status`
- `/api/bot/start`
- `/api/bot/stop`
- `/api/bot/status`
- `/api/bot/backtest`
- `/api/bot/simulate`
- `/api/bot/brain`
- `/api/metrics`

### AI Shadow
- `backend/ai_shadow.py`
- `backend/ai_shadow_feed.py`
- evaluate
- non-LIVE gate
- strategy + risk
- confidence threshold
- virtual trades
- memory/audit/statistics
- open-trade monitoring
- SL/TP
- settlement
- public CCXT feed start/stop/status

### Real exchange architecture
- `backend/exchange_service.py`
- authenticated CCXT clients
- credential validation
- exchange validation
- sandbox
- load markets
- balance
- create order
- cancel order
- execution gateway
- execution policy
- LiveControlState
- private CCXT executor

### Security / hidden modules
- `backend/security/execution_policy.py`
- `backend/security/execution_gateway.py`
- `backend/security/live_controls.py`
- `backend/security/request_policy.py`
- `backend/security/http_protection.py`
- `backend/security/credential_safety.py`
- `backend/security/safe_errors.py`
- `backend/execution_guard.py`
- `ccxt_guard.py`
- `live_guard.py`
- `live_trading_guard.py`

### Admin / installer / diagnostics
- `backend/admin.py`
- admin users/plugins/site/wallet/risk/live controls
- AI Shadow admin controls
- `backend/installer.py`
- `backend/install_service.py`
- `backend/health.py`
- `backend/health_check.py`
- `backend/health_endpoint.py`
- `backend/startup_check.py`
- `healthcheck.py`

### Frontend
- `/`
- `/home`
- `/login`
- `/register`
- `/forgot-password`
- `/dashboard`
- `/settings`
- `/marketplace`
- `/bot-management`
- `/wallet`
- `/admin`
- `style.css`
- `market_terminal.css`
- `market_live.css`
- `market_terminal.js`
- `market_live.js`
- `market_terminal_patch.js`

## Подтверждённые recovery targets

- installer HTTP flow / first-admin production flow
- CMSC debit/payment ledger
- persistent strategy activation
- complete ExchangeService → ExecutionGateway live UI
- unified kill switch semantics
- real background bot worker lifecycle
- authenticated `/api/bot/simulate`
- complete CSRF/rate-limit wiring
- authoritative execution policy after dependency tracing
- one authoritative exchange connection path
- Telegram token validation/connection contract
- durable bot runtime state
- complete UI exposure/verification for Dashboard/Wallet/Marketplace/Bot Management/Settings/Admin
- legacy/archived functionality after branch/import/caller/test tracing

## Target multi-exchange system

Use a capability-driven adapter architecture:

`ExchangeRegistry → ExchangeAdapter → Capabilities + MarketMetadata → Dynamic UI → ExecutionGateway`

The system should support all exchanges available through the installed CCXT/API adapter set rather than hard-coding a finite permanent list. Initial adapters should cover, where supported by the selected API layer, Binance, Bybit, OKX, KuCoin, Kraken, Coinbase, Gate.io, Bitget, MEXC, HTX, BingX, BitMart, CoinEx, Crypto.com, Deribit, Bitfinex, Gemini, WhiteBIT, Woo X and other available adapters.

Capabilities must include, where applicable:
- spot
- margin
- futures/swap
- options
- market/limit/stop/take-profit/OCO/trailing
- reduce-only/post-only
- hedge/one-way
- leverage
- isolated/cross
- long/short
- websocket/private websocket
- order/trade/position streams
- funding/open interest/mark/index price

When the exchange changes, the UI must query capabilities and automatically show/hide only the functions actually supported by that API.

## API key architecture

Settings → Exchanges:
- exchange
- API key
- secret
- passphrase where required
- sub-account where required
- sandbox/testnet
- detected permissions
- connection status
- last validation
- revalidate/delete

Secrets must be encrypted at rest, never returned to frontend, never logged, never sent to an LLM, and never stored in localStorage. Withdrawal permission must be disabled by default.

## Trading modes

### DEMO
Real market data, virtual money, no private orders.

### PAPER
Real market data, simulated execution including fees/slippage/latency.

### BACKTEST
Historical deterministic replay with fees/slippage and full performance metrics.

### SHADOW
Existing AI Shadow pipeline; never sends private orders.

### LIVE
Only mode allowed to send real private orders, and only through:
`Auth → RiskManager → ExecutionPolicy → LiveControlState → ExecutionGateway → ExchangeAdapter → Exchange`.

## Manual trading

The current `/api/trading/manual` is not yet a complete private exchange execution path. Keep its local validation/calculation behavior, then add explicit Demo/Paper/Test/Sandbox/Live routing. Never report FILLED until exchange confirmation exists.

Order lifecycle:
`CREATED → VALIDATED → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED` or `CANCELED/REJECTED/ERROR`.

## Professional chart / Pionex-style UX

Build a dark, dense, responsive trading terminal inspired by modern crypto exchanges and Pionex UX without copying branding/assets/code.

Chart must support:
- candles
- volume bars
- grid
- price/time scales
- crosshair
- hover OHLC
- zoom/pan/auto-fit/fullscreen
- drawing tools
- indicators
- order markers
- bot grid lines
- entries/exits
- SL/TP
- liquidation
- average position price
- current price
- strategy/AI signals
- alerts

Drawing tools: trend line, horizontal, vertical, ray, rectangle, Fibonacci retracement/extension, measurement, price alerts.

Indicators: SMA, EMA, WMA, VWAP, RSI, MACD, Bollinger, ATR, Stochastic, ADX, OBV, Volume Profile and strategy-specific overlays.

Terminal layout:
- top: exchange/account/market/symbol/timeframe/mode/status/balance
- left: watchlist/markets
- center: chart
- bottom: open orders/positions/history/bot orders/signals/risk/logs
- right: context-sensitive order/bot panel

## Bot platform

Bot Management must expose:
- create/start/pause/resume/stop
- close positions
- cancel orders
- emergency stop
- clone
- backtest
- paper/demo
- export report

Each bot shows:
- bot ID/name
- exchange/account/pair
- strategy
- mode/status
- PnL/ROI
- drawdown
- trades/win rate
- last signal
- risk state
- uptime

Bot chart overlays:
- grid levels
- pending/filled orders
- entry/exit
- average entry
- SL/TP/trailing
- trigger
- liquidation
- strategy signals

## Strategies

Keep existing:
- `pure_harvester`
- `high_frequency_momentum`
- `compound_defender`
- existing learning-generated `learned_adaptive_momentum`

Add professionally, without replacing the above:
- Grid
- DCA/Martingale-style
- Rebalancing
- Smart Trade
- Signal Bot
- future exchange-specific strategies where capabilities permit

Every strategy must declare its supported market types, required capabilities, risk profile, parameters and execution constraints.

## Grid target

Support upper/lower price, grid quantity, arithmetic/geometric spacing, investment, trigger price, stop loss, take profit, close conditions, release profit, rebalance, grid PnL, total PnL, fees and out-of-range state.

Pionex feature concepts such as trigger price, stop loss, bot close, AI backtesting, arithmetic/geometric spacing, profit release and order display on chart are UX/product references, not code to copy.

## DCA / Rebalancing / Smart Trade / Signal Bot

DCA: initial order, safety orders, deviation, volume/step scales, max orders, TP/SL, capital and drawdown limits.

Rebalancing: assets, target weights, periodic/threshold mode, trigger, minimum trade size, fee-aware rebalance and drift.

Smart Trade: planned entry, TP, SL, trailing, risk/reward, sizing, preview and execution state.

Signal Bot: external signal/webhook, mapping, direction, confidence, size, SL/TP, expiry and duplicate protection. All signals pass risk/execution policy.

## AI layer

AI may analyze market regime, indicators, news, sentiment, strategy performance, anomalies and confidence; suggest parameters and explain decisions. AI must never bypass StrategyManager, RiskManager, ExecutionPolicy or LiveControlState, must never receive raw credentials and must never claim guaranteed profit.

Target flow:
`Market Data → Indicators → StrategyManager → AI Analysis → RiskManager → ExecutionPolicy → ExecutionGateway → Exchange`.

## Risk

Existing RiskManager remains authoritative. Extend with max daily/weekly loss, max drawdown, max positions, max exposure per asset/exchange, max leverage, max order notional, loss-streak cooldown, circuit breaker, volatility/liquidity/spread filters, stale-data protection, websocket disconnect protection and API error breaker.

Unify kill-switch semantics so a global kill blocks new LIVE orders everywhere while preserving emergency-cancel semantics.

## Worker / persistence

Current `HFTBot.start/stop` is process-local and does not itself create a production background loop. Add a durable `BotManager/BotRuntime` architecture with heartbeat, reconnect, state persistence, recovery after restart, stale-data protection, duplicate-order protection and kill-switch compliance.

Persistent state: users, plugins, access, memory, trades, stats, audits, wallet, settings, exchange connections, strategy configs and bot configs.

Runtime state: websocket/cache/process state. Never treat process-local runtime as authoritative production state.

## Backtest metrics

Required: initial/final capital, net PnL, ROI, max drawdown, Sharpe, Sortino, win rate, loss rate, profit factor, average trade/win/loss, consecutive wins/losses, fees, slippage, trades, exposure and equity curve.

Do not expose a field named `monthly_return_pct` as `roi` for a 365-day test.

## Health

Expose and verify real HTTP endpoints:
- `/health`
- `/health/live`
- `/health/ready`
- `/health/db`
- `/health/exchange`
- `/health/websocket`
- `/health/execution`
- `/health/version`

No secrets in health responses.

## Testing

Unit: strategy/risk/exchange/capabilities/orders/credentials/memory/PnL/metrics.

Integration: FastAPI/DB/exchange/strategy/bot/risk/execution.

HTTP: real route calls, not import-only checks.

E2E: register → login → exchange → symbol → chart → strategy → backtest → demo → paper → shadow → risk block → sandbox → order lifecycle → history → stop → kill switch.

Security: secret leakage, CSRF, auth/roles, rate limits, replay, duplicate orders, privilege escalation, live-mode bypass and kill-switch bypass.

## Deployment

Preserve existing adapters: Netlify, Docker, Render, Railway, Fly.io, Heroku/Procfile, Vercel, Codespaces/devcontainer. For serverless, do not rely on SQLite as permanent writable production storage or on process-local workers.

## AI Coder workflow

For every change:
1. Read the current file.
2. Trace imports/callers.
3. Trace template/JS callers.
4. Trace tests.
5. Trace duplicate implementations.
6. Select authoritative implementation.
7. Make minimal additive change.
8. Run unit/integration tests.
9. Run HTTP smoke.
10. Record result in `CMS_WORK`.

Never delete legacy modules before dependency tracing. Never remove endpoints because the current UI does not call them. Never silently change strategy names, execution modes or risk limits. Never simulate LIVE and label it LIVE.

## Definition of Done

A release is not “done” until BUILD, TEST, HTTP, UI, DB, EXCHANGE, BOT, STRATEGY, RISK, SECURITY and DEPLOYMENT are all PASS with evidence.

## Final architecture

```text
Frontend
  ↓
FastAPI API
  ├── MarketDataService → Chart/OrderBook
  ├── StrategyManager → AI Layer
  ├── CMS Engine → Memory/Trade/Stats/Audit
  └── Auth/Admin
             ↓
        RiskManager
             ↓
      ExecutionPolicy
             ↓
      LiveControlState
             ↓
      ExecutionGateway
             ↓
       ExchangeAdapter
             ↓
       REST/WebSocket
             ↓
          Exchange
```

## Final instruction

CMS-my is an existing trading CMS, not a greenfield app. The goal is to restore lost functionality, expose hidden backend capabilities, connect existing modules, build a professional multi-exchange trading terminal and strengthen the bot/AI system without changing the original bot concept.
