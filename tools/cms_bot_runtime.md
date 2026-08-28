# Bot Runtime — план

## Цель
Добавить фоновый цикл торговли для бота (H-08, H-09), чтобы:
- бот делал сделки в DEMO на реальных данных,
- demo сделки фиксировались в истории (trade_count растёт),
- логика Bot+AI (bot.py, hft_brain.py) не изменяется.

## Архитектура
`backend/bot_runtime.py` — `BotRuntime`:
- start/stop/pause/resume/emergency_stop
- lifecycle: DRAFT/VALIDATING/READY/RUNNING/PAUSED/STOPPING/STOPPED/ERROR/EMERGENCY_STOP
- каждый tick: market signal → risk check → strategy.execute(demo) → record_trade → update demo_balance / bot simulate
- kill switch integration: respect risk_manager.kill_switch и LiveControlState
- persistence: запись сделок через engine.record_memory + Trade model (mode=demo)

## Интеграция (additive)
- main.py: `runtime = BotRuntime(...)`, `/api/bot/start` вызывает `runtime.start()` (в доп. к bot.start)
- `/api/bot/status` добавит `lifecycle`, `trade_history`
- не трогаем bot.py/hft_brain.py

## Риски
- потокобезопасность SQLite: использовать engine session-per-call
- процесс-local (serverless не держит потоки) — acceptable для codespace/local + Docker
