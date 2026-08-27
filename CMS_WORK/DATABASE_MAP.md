# CMS-my — DATABASE MAP (SQLite, sqlalchemy models in cms_core.py)

## Таблицы (ORM)

### users
- id (PK)
- email (unique)
- password_hash
- kyc_status (bool)
- role (default "user")

### plugins
- id (PK)
- name (unique)
- price
- description

### user_plugins
- id (PK)
- user_id (FK users)
- plugin_id (FK plugins)
- active (bool)
- purchased_at
- access_until

### learning_memory
- id (PK)
- user_id (string, not FK)
- action
- result (float)
- context (text)
- created_at

### bot_stats
- id (PK)
- name
- value (string)
- created_at

### audit_logs
- id (PK)
- user_id (string)
- action
- context (text)
- created_at

### wallets
- id (PK)
- user_id (FK users, unique)
- credits (float, default 0)
- wallet_provider, wallet_address
- exchange_provider, exchange_key_masked, exchange_sandbox (bool)
- exchange_provider_arb, exchange_key_masked_arb, exchange_sandbox_arb (bool) — второй API для арбитража
- telegram_username
- updated_at

### trades
- id (PK)
- user_id (FK users)
- pair
- mode
- strategy
- pnl (float)
- balance (float)
- created_at

### site_settings (key/value)
- key (PK)
- value (text)

### demo_sessions
- id (PK)
- user_id (FK users, unique)
- demo_active (bool)
- demo_balance (float, default 100)
- demo_pnl (float)
- demo_trades_count (int)
- created_at, updated_at

### strategy_templates
- id (PK)
- user_id (FK users)
- name
- description
- strategy_type (default "pure_harvester")
- leverage, risk_tolerance, fee_rate
- parameters (json text)
- is_public (bool)
- trial_days (default 15)
- price_eur
- created_at

## Отсутствующие сущности (нужны для полной реализации ТЗ)
- bots (конфигурация/состояние/позиции/ордера/heartbeat)
- copy_trading (провайдеры/подписчики/настройки/история копирования)
- notifications
- payment_ledger / CMSC_accounting
- exchange_accounts (несколько аккаунтов на биржу)
- strategy_parameters (версионированные схемы параметров)
- orders (lifecycle: CREATED→VALIDATED→SUBMITTED→FILLED/PARTIAL/CANCELED)
- positions (для futures/margin)
