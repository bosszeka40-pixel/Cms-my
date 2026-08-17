# CMS-my — Project Status

> Единый журнал состояния проекта. Обновлять при каждом существенном изменении.
>
> **Правило:** `DONE` означает только проверенное состояние. Если код написан, но тест/интеграционная проверка не пройдены — статус `VERIFY`.

## Status legend
- `DONE` — сделано и проверено
- `VERIFY` — сделано, но требует проверки
- `IN PROGRESS` — сейчас в работе
- `TODO` — запланировано
- `BLOCKED` — нельзя продолжать без дополнительной информации/решения
- `LEGACY` — старый код; не удалять, пока не подтверждена зависимость

## Current branch
- `cleanup/security-hardening-2026-08`
- `main` не изменять напрямую во время этого этапа.

## Installation / Admin
- [ ] `IN PROGRESS` — подключить HTTP `/install` к реальной модели `User` и существующей БД.
- [x] `VERIFY` — сервис создания первого admin использует существующую модель `User`/`CMSEngine`.
- [x] `VERIFY` — повторная установка блокируется installation marker.
- [x] `VERIFY` — добавлен интеграционный regression test installer.
- [ ] `TODO` — создать UI/HTTP маршрут `/install`.
- [ ] `TODO` — нормальный admin login без DEV bypass в production.
- [ ] `TODO` — DEV bypass оставить только для development и сделать explicit opt-in.

## Security
- [x] `DONE` — production требует `SECRET_KEY`.
- [x] `DONE` — production session cookies могут быть `https_only`.
- [x] `DONE` — OAuth state проверяется.
- [x] `VERIFY` — добавлен password migration layer: scrypt для новых паролей + автоматическая миграция старого SHA-256 после успешного входа.
- [ ] `TODO` — CSRF-защита браузерных POST.
- [ ] `TODO` — rate limiting login.
- [ ] `TODO` — проверить авторизацию всех `/api/*` endpoints.
- [ ] `TODO` — проверить права admin/operator/viewer.
- [ ] `TODO` — безопасное хранение credentials бирж.
- [ ] `VERIFY` — обновлённые Python dependencies должны пройти полный CI.

## CMS / UI ↔ Backend
- [x] `VERIFY` — обнаружена причина отсутствия свечей: frontend ожидал массивы OHLC, а `/api/market/history` возвращает объекты `{timestamp, open, high, low, close, volume}`.
- [x] `VERIFY` — добавлен отдельный exchange-style canvas renderer с OHLC, объёмом, сеткой, ценовой шкалой и hover tooltip.
- [x] `VERIFY` — график адаптируется к DPR/resize и обновляет историю каждые 15 секунд.
- [x] `VERIFY` — добавлен UI-режим `LIVE · 1 сек`.
- [x] `VERIFY` — для Binance live-режим собирает реальные trade events в односекундные OHLCV-свечи через WebSocket.
- [x] `VERIFY` — для других бирж live-режим использует ticker fallback с интервалом 1 сек; это не заменяет полноценный trade stream.
- [ ] `IN PROGRESS` — составить карту всех страниц, шаблонов и backend routes.
- [ ] `TODO` — проверить Dashboard.
- [ ] `TODO` — проверить Wallet.
- [ ] `TODO` — проверить Marketplace.
- [ ] `TODO` — проверить Bot management.
- [ ] `TODO` — проверить Settings.
- [ ] `TODO` — проверить Admin.
- [ ] `TODO` — проверить Login/Register/Social login.
- [ ] `TODO` — проверить тему Light/Dark.
- [ ] `TODO` — восстановить функции, которые есть в backend, но отсутствуют в шаблонах.
- [ ] `TODO` — не удалять существующие UI-функции без подтверждения зависимости.

## Backend / Trading
- [ ] `TODO` — полный аудит API endpoints.
- [ ] `VERIFY` — проверки входных данных HFT/strategy/risk модулей.
- [ ] `TODO` — проверить exchange connection flow.
- [ ] `TODO` — проверить simulation/paper/live режимы.
- [ ] `TODO` — проверить kill switch.
- [ ] `TODO` — проверить risk limits.
- [ ] `TODO` — не заявлять гарантированную прибыль; стратегии должны иметь явные risk/disclaimer boundaries.

## Database / Legacy
- [ ] `IN PROGRESS` — определить единственную актуальную БД и все места её использования.
- [ ] `LEGACY` — старые базы: не удалять до подтверждения зависимости.
- [ ] `LEGACY` — второй/старый `main.py`: не удалять до подтверждения entry point.
- [ ] `LEGACY` — `archive/`: не удалять функциональность без проверки ссылок.
- [ ] `TODO` — после аудита удалить только подтверждённый legacy.

## Existing changes — verify
- [x] `VERIFY` — добавлен `backend/installer.py`.
- [x] `VERIFY` — добавлен `backend/install_service.py`.
- [x] `VERIFY` — добавлен `backend/password_compat.py`.
- [x] `VERIFY` — добавлен `templates/install.html`.
- [x] `VERIFY` — добавлены installer tests.
- [x] `VERIFY` — добавлены `static/market_terminal.js` и `static/market_terminal.css` для исправления/улучшения биржевого графика.
- [x] `VERIFY` — добавлены `static/market_live.js` и `static/market_live.css` для live 1s режима.
- [ ] `VERIFY` — первая уборка legacy/pycache требует полного regression run.
- [ ] `VERIFY` — Render/dependency/security изменения требуют полного CI.

## Before merge
- [ ] Полный unit test suite.
- [ ] Installer integration test.
- [ ] Login/admin regression tests.
- [ ] UI route/template smoke test.
- [ ] API authorization regression test.
- [ ] Production configuration check.
- [ ] Проверка, что существующие функции CMS не потеряны.
- [ ] Проверка графика свечей на реальном API и разных таймфреймах.
- [ ] Проверка live 1s режима на Binance и fallback на других биржах.
- [ ] Проверка мобильного отображения терминала.
- [ ] Только после этого — review и merge в `main`.

## Notes
- DEV-вход без пароля был временным и нужен для разработки. Не ломать его без замены installer/admin flow.
- Приоритет: сохранить существующий функционал → исправить безопасность → восстановить отсутствующий UI → удалить подтверждённый legacy.
- Не считать `VERIFY` завершённым, пока код не прошёл тесты и интеграционную проверку.
- `LIVE · 1 сек` — это рыночное отображение, а не обещание исполнения ордеров с задержкой ровно 1 сек. Реальная задержка зависит от WebSocket/биржи/сети.
