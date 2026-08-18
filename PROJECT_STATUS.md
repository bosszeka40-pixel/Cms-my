# CMS-my — Project Status

> Единый журнал состояния проекта. Обновлять при каждом существенном изменении.
> **Правило:** `DONE` означает только проверенное состояние. Если код написан, но тест/интеграционная проверка не пройдены — статус `VERIFY`.

## Status legend
- `DONE` — сделано и проверено
- `VERIFY` — сделано, но требует проверки
- `IN PROGRESS` — сейчас в работе
- `TODO` — запланировано
- `BLOCKED` — нельзя продолжать без дополнительной информации/решения
- `LEGACY` — старый код; не удалять, пока не подтверждена зависимость
- `CANDIDATE` — подозрительно лишний/дублирующий код; сначала проверить ссылки

## Current branch
- `cleanup/security-hardening-2026-08`
- `main` не изменять напрямую во время этого этапа.

## Current work rule
- Сначала рабочая функциональность и серверный тест.
- Безопасность — отдельным этапом после функционального прогона.
- Simulation/paper-код не считать конечным trading flow; использовать только для тестов, пока не подтверждён live flow.
- Не удалять код по внешнему виду. Кандидаты сначала записываются в `LEGACY_REVIEW.md`, затем проверяются по ссылкам/тестам.

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
- [x] `VERIFY` — market terminal/live assets продублированы в активном `frontend/` static mount.
- [x] `VERIFY` — добавлен compatibility patch для legacy market controls.
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
- [x] `VERIFY` — проверки входных данных HFT/strategy/risk модулей.
- [ ] `IN PROGRESS` — проверить реальный exchange connection flow и свести дублирующую логику с `exchange_service`.
- [ ] `VERIFY` — simulation/paper-код помечен как кандидат на удаление/изоляцию после проверки зависимостей.
- [ ] `TODO` — проверить kill switch.
- [ ] `TODO` — проверить risk limits.
- [ ] `TODO` — не заявлять гарантированную прибыль; стратегии должны иметь явные risk/disclaimer boundaries.

## Legacy cleanup
- [x] `DONE` — создан `LEGACY_REVIEW.md` с кандидатами и правилами удаления.
- [ ] `VERIFY` — `HFTSimulatePayload` и `/api/bot/simulate`: найти все frontend/test ссылки; затем изолировать или удалить, если не нужны для тестов.
- [ ] `VERIFY` — inline exchange connection в `/marketplace`: сравнить с `exchange_service`; оставить один источник истины.
- [ ] `VERIFY` — `DEV_ADMIN_BYPASS`: не удалять до готового installer/admin flow.
- [ ] `VERIFY` — `forgot_password_submit`: проверить требуемый функционал перед заменой/удалением.
- [ ] `LEGACY` — `archive/`: не удалять функциональность без проверки ссылок.
- [ ] `TODO` — после аудита удалить только подтверждённый legacy.

## Database / Legacy
- [ ] `IN PROGRESS` — определить единственную актуальную БД и все места её использования.
- [ ] `LEGACY` — старые базы: не удалять до подтверждения зависимости.
- [ ] `LEGACY` — второй/старый `main.py`: не удалять до подтверждения entry point.

## Before merge / test gate
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
- DEV-вход без пароля временный и нужен для разработки. Не ломать его без замены installer/admin flow.
- Приоритет: сохранить существующий функционал → исправить безопасность → восстановить отсутствующий UI → удалить подтверждённый legacy.
- Не считать `VERIFY` завершённым, пока код не прошёл тесты и интеграционную проверку.
