# Точные ошибки для исправления — 26.08.2026

## 1. Отсутствующие API (вызывают 404 в консоли браузера)
Это и есть "file not found" ошибка — JS на страницах обращается к API, которых нет.

### Страница Кошелёк (`/wallet`)
- JS вызывает `GET /api/wallet/balance` → 404

### Страница Настройки (`/settings`)  
- JS может вызывать `GET /api/settings` → 404

### Страница Демо (`/demo`)
- JS вызывает `GET /api/demo/balance` → 404
- JS вызывает `GET /api/demo/history` → 404

### Страница Бот (`/bot-management`)
- JS вызывает `GET /api/bot/config` → 404

### Страница Маркетплейс (`/marketplace`)
- JS вызывает `GET /api/market/trending` → 404

## 2. Внешний доступ
- Сервер слушает на `0.0.0.0:8000` 
- Внешний IP `5.241.153.115` — порт закрыт файрволом
- cloudflared установлен в `/usr/local/bin/cloudflared`
- Нужно запустить: `cloudflared tunnel --url http://127.0.0.1:8000`

## 3. GitHub Push
- Текущая авторизация: `jevvgenij-coder`
- Нужна авторизация: `bosszeka40-pixel`
- Решение: `gh auth login` или use token

## Что нужно сделать (порядок)
1. Добавить API заглушки в `backend/main.py` для всех 404-эндпоинтов
2. Запустить `cloudflared tunnel` для публичного доступа  
3. Push в GitHub
4. Проверить все функции на живом сайте
