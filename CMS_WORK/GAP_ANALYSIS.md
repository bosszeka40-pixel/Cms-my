# CMS-my — GAP ANALYSIS (2026-08-27)

Формат: Function | Status | Location | Problem | Required change | Risk
Вместо перечисления всех 67 пунктов сразу — фокус на критических восстановлениях и высокоприоритетных дополнениях.

## Phase 1 — CRITICAL (подключить к main.py, gateway + persistence)
- Function: Health routing (C-01)
  Status: BROKEN
  Location: backend/health.py routes NOT registered in app
  Problem: health endpoints exist but app не mounting их через HTTP
  Required change: подключить health_router в main.py, добавить /health/live, /health/ready, /health/db, /health/exchange, /health/websocket, /health/execution, /health/version
  Risk: MEDIUM

- Function: Unauthenticated /api/bot/simulate (C-02)
  Status: UNSAFE
  Location: /api/bot/simulate — нет @require_user
  Problem: Endpoint аутентифицирован неверно, любой может вызывать симуляцию
  Required change: добавить _require_user(request) или role check
  Risk: HIGH

- Function: Duplicate exchange connection path (C-03)
  Status: DUPLICATE
  Location: marketplace + api/user/connect-exchange обошли ExchangeService
  Problem: два независимых пути подключения бирж, одна не валидируется
  Required change: уsingle authoritative ExchangeService path, убрать дубликат marketplace path
  Risk: HIGH

- Function: Browser CSRF (C-04)
  Status: MISSING
  Location: Всякие browser POST routes без CSRF middleware
  Problem: CSRF только в admin live-controls, общий browser — нет
  Required change: добавить единый CSRF middleware для всех state-changing routes
  Risk: HIGH

- Function: Split kill switches (C-05)
  Status: BROKEN
  Location: RiskManager kill switch + LiveControlState kill switch разделены
  Problem: Global block не работает единотворно
  Required change: объединить semantics: global kill блокирует все LIVE order везде
  Risk: HIGH

- Function: Manual trading semantic error (C-06)
  Status: BROKEN
  Location: /api/trading/manual — возвращает "executed" без реального ордера
  Problem: Never report FILLED until exchange confirmation exists
  Required change: возврат status "submitted"/"validated"/"pending"; LIVE gateway только для real orders
  Risk: HIGH

## Phase 2 — HIGH (backend/functional recovery)
- Function: CMSC payment ledger (H-04)
  Status: MISSING
  Location: Plugin purchase — debits CMSC debit/payment ledger нет
  Problem: Order extends UserPlugin access но не списывает credits, нет ledger
  Required change: добавить atomic debit, create payment/ledger record
  Risk: HIGH

- Function: Strategy persistence (H-06)
  Status: MISSING
  Location: save_strategy_config() не persists через restart/serverless
  Problem: Activated strategy config memory-only, уходит при рестарте
  Required change: persist in DB (site_settings/strategy_templates metadata)
  Risk: HIGH

- Function: Telegram contract (H-07)
  Status: BROKEN
  Location: UI collects token+username, backend не validates complete contract
  Problem: Username persisted, но контракт Telegram API не валидирован
  Required change: validate токен через Telegram API, remove unused fields
  Risk: MEDIUM

- Function: Process-local bot state (H-08)
  Status: MISSING
  Location: HFTBot.start/stop — process-local, no persistent state
  Problem: config/positions/heartbeats/PnL/runtime only в памяти
  Required change: durable BotManager/BotRuntime architecture, persistence SQLite
  Risk: HIGH

- Function: Bot lifecycle (H-09)
  Status: MISSING
  Location: start/stop toggles boolean, no real worker lifecycle
  Problem: boolean flag не представляет активного работающего бота
  Required change: real background loop, heartbeat, reconnect, kill-switch compliance
  Risk: HIGH

- Function: Multiple CMSEngine instances (H-10)
  Status: BROKEN
  Location: main.py + admin.py instantiates separate CMSEngine objects
  Problem: potential init/session drift across services
  Required change: centralize DB/session config
  Risk: MEDIUM

## Phase 3 — MEDIUM (UI + UX exposure)
- Function: UI exposure/verification (24 items)
  Status: PARTIAL
  Location: admin.html, bot_management.html, manual_trading.html, marketplace.html, demo.html, strategies.html — NOT updated под Pionex-style
  Problem: дизайн не обновлен, но и не ломан — preserve existing
  Required update: UI/UX polish per spec (but NOT redesign visual language)
  Risk: LOW

- Function: Theme modes (light/dark/auto)
  Status: EXISTS
  Location: static/style.css, templates/base.html
  Problem: Работает, но проверка интегрирована в profile/settings
  Risk: LOW

## Phase 4 — LOW (enhancements per TZ)
- Function: Full strategy parameters display
  Status: PARTIAL
  Location: templates/strategies.html показывает только name, параметры скрыты
  Problem: При выборе стратегии параметры не показываются (риск, стоп-лосс, диапазон)
  Required: Strategy editor/schema + Show all parameters button + Advanced mode
  Risk: MEDIUM

- Function: Demo mode verification (bot makes trades)
  Status: MISSING
  Location: Demo mode существует (/api/demo/trade, toggle), но бот не делает сделок в демо
  Required: Ensure bot creates at least one trade in demo, simulate engine models fills/fees/slippage
  Risk: HIGH

- Function: Copy Trading
  Status: PARTIAL
  Location: /copy-trading page есть, но копирует параметры стратегии, а не сделки/позиции
  Required: Full copy-trading dashboard + risk guard + trade copying (not just strategy params)
  Risk: HIGH

- Function: Pionex-style functional additions
  Status: PLANNED
  Location: Market, Bots pages
  Problem: Add Grid, DCA, Rebalancing, Smart Trade, Signal Bot, trigger price, SL/TP, profit release, chart order markers
  Risk: MEDIUM

- Function: Responsive design (mobile/tablet)
  Status: PARTIAL
  Location: style.css, base.html have some mobile адаптив, но неполный
  Required: Desktop full terminal, tablet reduced panels, mobile main actions only
  Risk: MEDIUM

- Function: API error handling (500 → friendly message)
  Status: BROKEN
  Location: 500 Internal Server Error показывается вместо info
  Required: Показывать user-friendly: "Binance API unavailable. Last sync: ... Retry"
  Risk: MEDIUM

## Summary
Критические восстановления (C-01..C-06): 6 штук, HIGH/MEDIUM risk
Высокие recovery (H-01..H-10): 10 штук, MEDIUM/HIGH risk  
Остальные (UI/UX, feature additions): PARTIAL/LOW risk

All changes: additive, no deletion, no wholesale branch merge, preserve existing functionality.
