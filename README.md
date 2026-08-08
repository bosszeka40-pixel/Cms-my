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

## Тестовые метрики

- Initial Capital: €100.00
- Final Capital: €109.20
- Total Net ROI: 9.20%
- Total Memory-Guided Trades: 444
- Win Rate: 93.9%
- Leverage: 4.0x
- Active Trading Knowledge: VSA, Order Flow, Liquidity Sweeps, Compound
