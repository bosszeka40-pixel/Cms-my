# Отчёт проверки сайта — 2026-08-26

## Статус сервера
- Сервер запущен: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Health check: `GET /health` → `{"status":"ok"}`
- Внешний IP: `5.241.153.115` — порт 8000 **НЕ ДОСТУПЕН** снаружи (файрвол)

## Результаты проверки страниц (все HTTP 200)
| Страница | Статус |
|---|---|
| `/` (Главная) | ✅ 200 |
| `/login` | ✅ 200 |
| `/register` | ✅ 200 |
| `/dashboard` | ✅ 200 |
| `/settings` | ✅ 200 |
| `/marketplace` | ✅ 200 |
| `/bot-management` | ✅ 200 |
| `/manual-trading` | ✅ 200 |
| `/strategies` | ✅ 200 |
| `/demo` | ✅ 200 |
| `/testing` | ✅ 200 |
| `/wallet` | ✅ 200 |
| `/admin` | ✅ 200 |
| `/forgot-password` | ✅ 200 |

## Статические файлы (все HTTP 200)
- `style.css`, `market_terminal.css`, `market_live.css`, `terminal.css`
- `market_terminal.js`, `market_live.js`, `market_terminal_patch.js`
- `trading_chart.js`, `cms_sections.js`

## API-эндпоинты — Проблемные (404 Not Found)
- `GET /api/wallet/balance` → **404** — маршрут не определён
- `GET /api/bot/config` → **404** — маршрут не определён
- `GET /api/exchanges` → **404** — маршрут не определён
- `GET /api/market/trending` → **404** — маршрут не определён
- `GET /api/demo/balance` → **404** — маршрут не определён
- `GET /api/demo/history` → **404** — маршрут не определён
- `GET /api/admin/settings` → **404** — маршрут не определён
- `GET /api/settings` → **404** — маршрут не определён
- `GET /api/test` → **404** — маршрут не определён
- `GET /api/install` → **404** — маршрут не определён
- `GET /api/logout` → **404** — маршрут не определён
- `GET /api/profile` → **404** — маршрут не определён
- `GET /api/admin/stats` → **404** — маршрут не определён
- `GET /api/wallet/connect` → **404** — маршрут не определён
- `GET /api/market/listings` → **404** — маршрут не определён
- `GET /api/notifications` → **404** — маршрут не определён
- `GET /api/feedback` → **404** — маршрут не определён

## API-эндпоинты — Рабочие (200)
- `GET /api/bot/status` → 200 ✅
- `GET /api/bot/brain` → 200 ✅
- `GET /api/bot/memory` → 200 ✅
- `GET /api/market/news` → 200 ✅
- `GET /api/market/data` → 200 ✅
- `GET /api/market/signal` → 200 ✅
- `GET /api/strategies` → 200 ✅
- `GET /api/strategies/public` → 200 ✅
- `GET /api/metrics` → 200 ✅
- `POST /api/chat` → 200 ✅

## Основные находки
1. **Сайт работает локально** — все страницы и статика отдают 200
2. **Ошибка "file not found"** — пользователь пытается открыть сайт снаружи, но порт 8000 закрыт файрволом
3. **GitHub push заблокирован (403)** — авторизован как `jevvgenij-coder`, репозиторий принадлежит `bosszeka40-pixel`
4. **Многие API-эндпоинты отсутствуют** — JS может вызывать несуществующие API → ошибки в консоли браузера
