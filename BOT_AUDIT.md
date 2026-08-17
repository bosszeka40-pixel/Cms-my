# CMS-my — Bot Runtime/Architecture Audit

Branch: `cleanup/security-hardening-2026-08`
Date: 2026-08-17

## Important conclusion

The project already contains substantially more bot/memory functionality than the current UI suggests. Do **not** replace it with a newly invented memory/learning architecture before integrating and testing what already exists.

## Components found

### 1. HFTBot (`backend/bot.py`)
- `start()` only sets `active=True` and appends a `started` event.
- `stop()` only sets `active=False` and appends a `stopped` event.
- `status()` returns in-memory status/stat events.
- `simulate()` records simulated trade results in in-memory `stats`.
- There is currently no continuous background market loop in this class.

**Status: VERIFY / likely UI-orchestration layer, not the full trading engine.**

### 2. CMSProductionHFTBot + AICryptoMemoryBrain (`backend/hft_brain.py`)
- `CMSProductionHFTBot.trade_loop()` consumes aligned `market_data` and `ai_stream` arrays.
- Validates finite values, positive prices, series length, and leverage <= 2x.
- Uses past/current point `i` to create a signal and `i+1` only to settle the trade.
- Records each executed simulation in `trade_history`.
- `AICryptoMemoryBrain` keeps `memory_history` with action, ROI and timestamp.
- `summarize()` exposes action count/history.

**Important:** this brain memory is process-local and is not the same as the persistent CMS learning memory.

**Status: EXISTING FUNCTIONALITY — preserve and integrate.**

### 3. Persistent learning memory (`backend/cms_core.py`)
Database model `LearningMemory` exists with:
- `user_id`
- `action`
- `result`
- `context`
- `created_at`

`CMSEngine.record_memory()` persists memory in `cms_core.db`.
`recent_memories()` retrieves recent observations and also includes global (`user_id IS NULL`) memories for a user.

There is already a learning hook:
- when `action == "strategy_test"` and result > 0,
- after at least 3 profitable strategy tests,
- a `learned_adaptive_momentum` plugin is created if it does not already exist.

**Important:** this is a rule-based learning/strategy-generation mechanism, not evidence of machine-learning model training.

**Status: EXISTING FUNCTIONALITY — preserve; audit behavior before changing.**

### 4. Strategy execution (`backend/modules/strategy_manager.py`)
Existing strategies include:
- `pure_harvester`
- `high_frequency_momentum`
- `compound_defender`

The manager:
- loads YAML configuration;
- validates leverage and fee rate;
- executes strategy-specific module logic;
- calculates fees;
- returns signal, P&L, balance, leverage and strategy name.

**Status: EXISTING FUNCTIONALITY — integrate into terminal instead of duplicating.**

### 5. Trading test flow (`backend/main.py`)
`POST /api/trading/test` currently does:
1. authenticate user;
2. pass risk gate;
3. validate pair;
4. execute `StrategyManager`;
5. record simulated trade in `HFTBot`;
6. persist `strategy_test` into `LearningMemory`;
7. persist trade into `Trade`;
8. record risk result.

This is the clearest existing path connecting strategy → bot → memory → trade history → risk.

### 6. Production/HFT simulation API
`POST /api/bot/simulate` calls `CMSProductionHFTBot.trade_loop()` and then records an HFT simulation statistic.

`GET /api/bot/brain` exposes the brain summary, currently admin-only.

### 7. Market analysis already present
Existing endpoints include:
- `/api/market/data`
- `/api/market/history`
- `/api/market/news`
- `/api/market/signal`

`/api/market/data` already combines ticker + order book + candles.
`/api/market/history` returns normalized `candles` and currently supports `1m`, `5m`, `15m`, `1h`, `1d`.

## Key gaps discovered

1. `HFTBot.start()` does not itself start a market-data/trading loop. It only changes state.
2. `AICryptoMemoryBrain.memory_history` is lost on process restart; persistent `LearningMemory` is separate.
3. The existing "learning" behavior creates a plugin after three profitable tests, but there is no evidence here of autonomous ML model training.
4. The terminal currently needs to consume the existing strategy/memory/risk pipeline rather than inventing a second bot architecture.
5. `/api/user/connect-exchange` currently accepts API credentials but is not yet wired into a full persisted/execution flow in this audit; this requires a dedicated security review before live trading.
6. Live 1-second trading data must remain separate from historical REST candles; real trade-stream data is needed for true 1s OHLCV.

## Required next audit

- Trace every call from `bot_management.html` into the endpoints above.
- Trace every endpoint into `CMSEngine`, `StrategyManager`, `RiskManager`, and HFT brain.
- Verify whether UI controls labeled Live/Paper/Test actually correspond to distinct execution modes.
- Verify memory persistence across restart.
- Verify strategy learning trigger and whether the generated strategy can actually be activated/executed.
- Verify whether active strategy configuration is persisted safely.
- Verify exchange credential storage and live-order boundaries.
- Add runtime tracing only after the application can be launched in a real test environment.

## Rule

**Do not replace existing bot memory/learning functionality until the above flow has been verified end-to-end.**
