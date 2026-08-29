# GIT STATUS 2026-08-29

## Репозиторий
- URL: `https://github.com/bosszeka40-pixel/Cms-my.git` (origin)
- Рабочая ветка: `feat/unified-bot-controls` → `HEAD = 08fd3c4`
- Коммиты ветки: `08fd3c4` (ApiUI-рендер) ← `5ae02ce` (unified bot controls) ← `00ffaca` (шаблон и чарт) ← ...
- origin/main (локальная копия): `e61006b`, «behind 13» — НЕ синхронизировано (см. рекомендации ниже).

## Коммит 08fd3c4
- Сообщение: `feat: unify pretty render of API panels across terminal pages via ApiUI`
- Статистика: 15 файлов, +1428 / −321
- Включено:
  - `static/api_render.js` (новый)
  - `static/style.css`
  - `templates/admin.html, bot_management.html, dashboard.html, demo.html, login.html, manual_trading.html, marketplace.html, profile.html, settings.html, strategies.html, testing.html, wallet.html`
  - `backend/config.yaml` (fee_rate 0.02→0.002, leverage 2.0→1.0)

## Push — ВЫПОЛНЕН ✔ (2026-08-29)
- Ветка `jeevgenij-coder-cms` успешно запушена на origin через PAT.
- `origin/jeevgenij-coder-cms` = `08fd3c4b0d4ac5ba0415499f48ab7274a0c7ce02` (08fd3c4).
- PR (опционально): https://github.com/bosszeka40-pixel/Cms-my/pull/new/jeevgenij-coder-cms
- Ссылки на создание токена (PAT, права `repo`): https://github.com/settings/tokens/new , список: https://github.com/settings/tokens . Рекомендуется отозвать использованный токен после завершения (он передавался в чате).

## Рекомендации (не выполнены, из аудита)
- Синхронизировать main с origin/main.
- Отключить `/login/dev-admin-bypass` на проде.
- Почистить мёртвый static JS и старые ветки.
- Объединить три поллера `/api/bot/status`.