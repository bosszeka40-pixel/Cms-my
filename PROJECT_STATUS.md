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
- [ ] `IN PROGRESS` — подключить `/install` к реальной модели `User` и существующей БД.
- [ ] `TODO` — создать первого администратора через installer.
- [ ] `TODO` — безопасное хэширование пароля и совместимость с существующими пользователями.
- [ ] `TODO` — после установки создать installation marker.
- [ ] `TODO` — заблокировать `/install` после завершения установки.
- [ ] `TODO` — нормальный admin login без DEV bypass в production.
- [ ] `TODO` — DEV bypass оставить только для development и сделать explicit opt-in.

## Security
- [x] `DONE` — production требует `SECRET_KEY`.
- [x] `DONE` — production session cookies могут быть `https_only`.
- [x] `DONE` — OAuth state проверяется.
- [ ] `TODO` — CSRF-защита браузерных POST.
- [ ] `TODO` — rate limiting login.
- [ ] `TODO` — проверить авторизацию всех `/api/*` endpoints.
- [ ] `TODO` — проверить права admin/operator/viewer.
- [ ] `TODO` — безопасное хранение credentials бирж.
- [ ] `VERIFY` — обновлённые Python dependencies должны пройти полный CI.

## CMS / UI ↔ Backend
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
- [ ] `VERIFY` — добавлен `backend/installer.py`.
- [ ] `VERIFY` — добавлен `templates/install.html`.
- [ ] `VERIFY` — добавлен `tests/test_installer.py`.
- [ ] `VERIFY` — выполнена первая уборка legacy/pycache.
- [ ] `VERIFY` — обновлены Render/dependency/security настройки в текущей ветке.

## Before merge
- [ ] Полный unit test suite.
- [ ] Installer integration test.
- [ ] Login/admin regression tests.
- [ ] UI route/template smoke test.
- [ ] API authorization regression test.
- [ ] Production configuration check.
- [ ] Проверка, что существующие функции CMS не потеряны.
- [ ] Только после этого — review и merge в `main`.

## Notes
- DEV-вход без пароля был временным и нужен для разработки. Не ломать его без замены installer/admin flow.
- Приоритет: сохранить существующий функционал → исправить безопасность → восстановить отсутствующий UI → удалить подтверждённый legacy.
