# АУДИТ 2026-08-28 — ПОЛНЫЙ ОТЧЁТ (БЕЗ ИСПРАВЛЕНИЙ)

Объём: репозиторий `/root/Documents/Codex/2026-08-25/500/Cms-my`, ветка `feat/unified-bot-controls`.
Цель: зафиксировать фактическое состояние, найти риски. Исправления НЕ вносились.

## 1. Репозиторий / Git
- Remote: `origin` = `https://github.com/bosszeka40-pixel/Cms-my.git` (без токена в URL).
- Локальный `main` отстаёт: `e61006b`, а `origin/main` = `90b8d21` (мерж PR #26). НЕ синхронизирован.
- Ветки: много старых remote-веток (backup/*, fix/*, work/*, audit/*, codex/* и др.) ≈ 20+; возможна засорённость. `jeevgenij-coder-cms` удалена на GitHub после мержа PR #26.
- Рабочее дерево: чистое.
- PR #27: open, `feat/unified-bot-controls → main`.
- Автор коммитов: `bosszeka40 <bosszeka40@users.noreply.github.com>`.

## 2. Структура проекта
- `templates/` 19 файлов, `static/` 9 файлов, `backend/` (Python) большая монолика `main.py` (~2141 строк) + модули.
- Данные: `cms_core.db` (303 KB), `cms_v12.db` (13.1 MB), БД продублированы в `backend/`.
- Отчётные MD в корне и `CMS_WORK/`: уже есть большой объём документации.

## 3. API: шаблоны vs бэкенд (проверка сходимости)
Все вызываемые из шаблонов эндпоинты НАЙДЕНЫ в бэкенде:
`/api/bot/status`, `/api/demo/trade`, `/api/market/signals`, `/api/bot/backtest`, `/api/trading/history`,
`/api/market/history`, `/api/market/data`, `/api/copy-trading/toggle`, `/api/arbitrage/scan`,
`/api/strategies/user`, `/api/chat`, `/api/bot/simulate` — каждый по 1 определению в `backend/main.py`.
- `arbitrageAction` вызывает `/api/arbitrage/{start|stop|scan}` — есть: `/api/arbitrage/start` (2090), `.../stop` (2096), `.../status` (2102), `.../scan` (2108).
- Admin live-controls: определены в `backend/admin.py` (`/api/admin/live-controls`, `/global`, `/bots/{id}`, `/ai-bots/{id}`, `/audit`), НЕ в main.py — вызов из шаблонов валиден.
- Динамический префикс в шаблонах (`/api/bot/`+action, `/api/arbitrage/`+action) — валиден.

## 4. Фронтенд
- HTML-баланс тегов: во всех 19 шаблонах `<div>`/`</div>`, `<button>`, `<table>` сбалансированы (проверено счётчиками).
- Внешние ресурсы: ТОЛЬКО `https://unpkg.com/lightweight-charts@4.1.1` (base.html:11). Сторонних ключей/трекинга нет.
- «Мёртвые» статические файлы (0 ссылок в шаблонах): `cms_sections.js`, `market_live.js`, `market_terminal.js`, `market_terminal_patch.js`. При этом CSS `market_live.css`, `market_terminal.css` подключены в base.html (v=8-mobile).
- Живой JS для графиков: `static/trading_chart.js` (используется терминалом и ботами). Дублирующийся WebSocket-механизм в `market_live.js` НЕ подключается (мёртвый код).
- Кэш-версия CSS: единая `v=8-mobile` во всех 7 подключениях.

## 5. Наблюдения по кнопкам (текущая реализация)
- `setBotState(true, 'PAUSED')` → кнопка «⏹ Остановить» + «▶ Продолжить» (пауза ≠ офф). Логика верна.
- Поллеры на бот-странице: 3 шт. (status-поллер строки 478 + pollBotStatus 5c + loadBotMarket 15c + loadBotTrades 10c). Дубль опроса `bot/status` (строки 478 и 592) — мелкая избыточность, НЕ критично.
- После старта/стопа кнопки переключаются оптимистично; если API вернёт `active` — состояние берётся из ответа (приоритет).
- Арбитраж: решение по «Обновить не обязательно», кнопка перерисовывается сервером при reload после `arbitrageAction`.

## 6. Безопасность (frontend-часть аудита)
- Секретов в шаблонах/static нет: найденные слова `api_key`/`api_secret`/`passphrase` — только поля ввода/чтение с сервера, не хардкод.
- `|safe` не используется в шаблонах (XSS-риск низкий).
- CSP/security-заголовки в `backend/main.py` не найдены (grep) — возможная рекомендация, НЕ исправлялась.
- `dev-admin-bypass` существует (`POST /login/dev-admin-bypass`, main.py:637) — потенциально высокая дыра в проде, помечена как замечание.

## 7. Прочее / риски
- Задержка графиков: `loadChartData` грузится ДО старта live-каплей (terminais: `loadChartData` → `startLivePrice`). LIVE включается кнопкой Timeframe `● LIVE`. Это as-is, параметры графика уже откачены.
- В конфиг remote URL токен не попадал; но токен фигурировал в истории сессии — рекомендуется ротация при необходимости.
- git политика: локальный `main` не обновлён после мержа (audit/служебное, не исправлялось).

## 8. Итог
- Функциональных «поломок» в моих изменениях не найдено.
- Замечания: дофабрикат (1) синхронизировать локальный main с origin/main; (2) убрать/деактивировать `dev-admin-bypass` на проде; (3) почистить мёртвый static JS и старые remote-ветки; (4) объединить дублирующиеся поллеры bot/status; (5) рассмотреть CSP-заголовки. Эти пункты — рекомендации, исправления не вносились.