# CMS-my — ARCHITECTURE MAP (Discovery, 2026-08-27)

Целевая архитектура (по master-spec) — единый multi-exchange trading terminal.
Существующая структура НЕ переписывается, добавляется поверх.

```text
Frontend (Jinja2 + JS, static/)
  ↓
FastAPI backend/main.py (роуты: страницы + /api/*)
  ├── MarketDataService (market_history.py, ccxt public)
  ├── StrategyManager (modules/strategy_manager.py)
  ├── CMSEngine (cms_core.py: users/plugins/wallet/trade/memory/audit/demo/strategy_templates)
  ├── RiskManager (risk_management.py)
  ├── HFTBot (bot.py) + CMSProductionHFTBot/AICryptoMemoryBrain (hft_brain.py)
  ├── AI Shadow (ai_shadow.py, ai_shadow_feed.py)
  ├── ExchangeService (exchange_service.py) + ExecutionGateway/Policy/LiveControls (security/)
  └── Admin router (admin.py)
             ↓
        RiskManager → ExecutionPolicy → LiveControlState → ExecutionGateway → ExchangeAdapter → Exchange
```

## Ключевые домены
- Пользователи/сессии/роли: `cms_core.py::User`, `main.py`
- Плагины/стратегии-плагины: `Plugin`, `UserPlugin`, `StrategyTemplate`
- Кошелёк CMSC + подключения бирж: `Wallet`
- Сделки: `Trade`
- Память обучения: `LearningMemory`
- Статистика/метрики бота: `BotStat`
- Аудит: `AuditLog`
- Демо-режим: `DemoSession`
- Настройки сайта: `SiteSetting`
- Рынок/свечи/новости: `market_history.py`
- Стратегии: `modules/strategy_manager.py`, `strategy_performance.py`
- Бот/HFT: `bot.py`, `hft_brain.py`
- Арбитраж: `modules/arbitrage_engine.py` (новая)
- Безопасность LIVE: `security/execution_policy.py`, `execution_gateway.py`, `live_controls.py`, `request_policy.py`, `http_protection.py`, `safe_errors.py`, `credential_safety.py`

## Текущие страницы (templates/)
index, login, register, forgot_password, base, dashboard, settings, marketplace,
bot_management, manual_trading, strategies, testing, demo, wallet, copy_trading,
arbitrage, admin, install

## Бэкенд модули (backend/)
main.py, admin.py, cms_core.py, bot.py, hft_brain.py, risk_management.py,
exchange_service.py, market_history.py, strategy_performance.py,
ccxt_guard.py, execution_guard.py, live_guard.py, live_trading_guard.py,
installer.py, install_service.py, health.py, health_check.py, health_endpoint.py,
startup_check.py, ai_shadow.py, ai_shadow_feed.py, trading_execution_gate.py,
config_validation.py, password_compat.py, modules/*

## Фронтенд (static/ + frontend/)
style.css, terminal.css, market_terminal.css, market_live.css, market_terminal.js,
market_live.js, market_terminal_patch.js, trading_chart.js, cms_sections.js
