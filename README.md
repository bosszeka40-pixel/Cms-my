# Daily Compound Harvester CMS

## Описание
Daily Compound Harvester — модульная CMS-платформа для тестовой HFT-торговли с AI-движком, управлением юзерами и выбором стратегий.

## Структура проекта
- `backend/` — FastAPI backend
- `backend/cms_core.py` — центральная база данных и модель пользователя/плагина
- `backend/admin.py` — API для управления пользователями и плагинами
- `backend/bot.py` — базовый HFT-блок для старта/стопа
- `backend/hft_brain.py` — AI Brain + production HFT-модуль
- `backend/modules/` — стратегия торгового движка
- `frontend/` — простая UI-страница для подключения бирж
- `requirements.txt` — зависимости проекта
- `Dockerfile` / `Procfile` — конфигурация для развертывания
- `ADVANCED_TEST_REPORT.md` — сохраненные показатели тестирования

## Быстрый старт

```bash
pip install -r requirements.txt
python run.py
```

Откройте в браузере:

```
http://127.0.0.1:8000
```

## Облачный деплой

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Главная точка входа: `run.py`

## Основные API

- `GET /api/report` — получить тестовый отчет `ADVANCED_TEST_REPORT.md`
- `GET /api/metrics` — получить текущее состояние бота и AI Brain
- `POST /api/strategy/execute` — выполнить стратегию на основе `news_sentiment`, `price_change`, `current_balance`
- `POST /api/bot/simulate` — запустить HFT-симуляцию
- `POST /api/user/connect-exchange` — подключить биржу через CCXT

## Реальная торговля через API

Подключение хранится только в памяти процесса; API-секреты не записываются в базу данных.
По умолчанию все ордера работают в `dry_run`. Для отправки ордера на биржу необходимо:

1. Подключить API-ключ с правами **trade**, без права вывода средств.
2. Сначала проверить подключение через sandbox/testnet (`POST /api/exchange/connect` с `sandbox: true`).
3. Явно включить `LIVE_TRADING_ENABLED=true`.
4. Передать одновременно `live: true` и `confirm_live: true` в `POST /api/trading/order`.

Лимит номинала одной live-сделки задается `MAX_ORDER_NOTIONAL` и по умолчанию равен `1000`.

Основные endpoints:

- `POST /api/exchange/connect` — подключение и проверка ключей (`exchange_name`, `api_key`, `api_secret`, опционально `api_password`, `sandbox`)
- `GET /api/exchange/status` — состояние подключения
- `GET /api/exchange/balance` — баланс подключенного аккаунта
- `POST /api/trading/order` — market/limit ордер; без `live` только проверка параметров
- `DELETE /api/trading/order/<id>?symbol=BTC/USDT` — отмена ордера

Для live-ордера без поля `amount` автоматически используется минимальный размер,
который сообщает биржа для выбранной пары (включая минимальную стоимость ордера).
Явно указанное количество ниже биржевого минимума отклоняется.

Поддерживается подключение Pionex через CCXT. Ключи принимаются только на время
подключения и хранятся в памяти процесса; в базе данных сохраняется только
название биржи и маскированная подсказка ключа.

Для live-режима используйте отдельный production secret и HTTPS. Никогда не передавайте ключи
через URL и не включайте право вывода средств.

## Тестовые метрики

- Initial Capital: €100.00
- Final Capital: €109.20
- Total Net ROI: 9.20%
- Total Memory-Guided Trades: 444
- Win Rate: 93.9%
- Leverage: 4.0x
- Active Trading Knowledge: VSA, Order Flow, Liquidity Sweeps, Compound
