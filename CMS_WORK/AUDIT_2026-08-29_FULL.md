# AUDIT 2026-08-29 — 100% полный аудит проекта Cms-my (READ-ONLY)

Дата: 2026-08-29. Требование: не менять ничего. Правок не вносилось; единственный созданный файл — этот отчёт.
Проверялись ОБА чекаута одного репозитория:
- **A** = `/root/Cms-my` (main@4f0ab88) — «главный» локальный;
- **B** = `/root/Documents/Codex/2026-08-25/500/Cms-my` (jeevgenij-coder-cms@d52cb4d) — рабочий/серверный (на нём живёт `python3 run.py`, 127.0.0.1:8000).

Области: git-целостность, backend+безопасность, frontend/статик, тесты/CI/деплой, runtime.

---

## 0. Вердикт по областям

| Область | Статус |
|---|---|
| Git-целостность | ✅ цела (мусор `.l2s.tmp_*` в .git/objects) |
| Runtime сервера (B) | ✅ работает: /health=200, /ready=200, / =200; API отвечают |
| Backend безопасности | 🔴 CRITICAL: бэкдор dev-admin-bypass, ложный `executed` у manual trade |
| Frontend | 🔴 HIGH: XSS без экранирования в ряде мест; дубли static/frontend |
| Тесты/CI/деплой | 🟠 не здоров: health-контракт только для A сломан (в B — ок), serverless без mangum |

---

## 1. GIT-целостность (обе копии)

- Рабочие деревья обоих чекаутов чисты; untracked нет (CMS_WORK в B закоммичен и запушен).
- Тегов нет, stash пуст, сабмодулей нет.
- Worktree: A + detached `/root/.codex/worktrees/36b3/Cms-my` @4f0ab88; B — только основной.
- `git fsck`: A чист; B — 3 безобидных dangling blob. Секретов в истории/дереве не найдено (grep по ghp_/sk-/BEGIN/по log -p).
- `origin/main` локально = удалённому `90b8d21` в обоих.
- **FINDING G1 (LOW)** — мусор в `.git/objects`: `.l2s.tmp_obj_*`/`.l2s.tmp_pack_*` — 34 шт (A), ~510 шт (B); `count-objects` показывает garbage 2.27/3.02 MiB. Данные не затронуты; косметическая чистка `git gc --prune` возможна позже.
- **FINDING G2 (INFO)** — A: main@4f0ab88 на 20 коммитов позади origin/main; B: local main на 13 позади. Это норм для ветки-снэпшота; `backup/local-main-2026-08-29` = 4f0ab88 уже на GitHub.
- **FINDING G3 (LOW)** — в корне закоммичен файл `render .yaml` (с пробелом), устаревший/битый дубль `render.yaml`.

## 2. BACKEND и безопасность

### Критично
| Severity | Файл:строка | Находка |
|---|---|---|
| CRITICAL | B main.py:637 / A main.py:426 | Бэкдор `POST /login/dev-admin-bypass`: админ-сессия без пароля при `APP_ENV != production`. Комментарий: «TODO убрать перед продакшн». В Render есть APP_ENV=production, но в локальном/Fly-деплое бэкдор активен |
| CRITICAL | B main.py:1409+ | `/api/trading/manual`: отдаёт `status:executed` и пишет сделку/аудит БЕЗ реального ордера (ложная сделка). В B вставлен вызов `submit_real_order(email, …)` — сигнатура неверна (ожидает executor-callable первым аргументом) → реальный live-ордер никогда не исполнится, падает fail-closed |
| HIGH | A main.py | Нет `@app.exception_handler(500)` → сырой traceback клиенту (в B эта правка есть — sanitized handler) |
| HIGH | все main.py | CSRF нет ни на одном POST/форме кроме 3 эндпоинтов admin live-controls (X-CSRF-Token). Атаки: kill-switch, бот start/stop, формы |
| HIGH | B/A main.py ~43 | Дефолтный `SECRET_KEY="development-only-change-me"` → подделка сессий, если env не задан |

### Средне
- Rate limiting НЕ подключён (классы `RateLimiter`/`enforce_rate_limit` есть, не вызваны) — DoS на /login, /register, /api/market/*, /api/chat.
- Публичные без auth: `GET /api/exchanges`, `/api/market/trending`, `/api/strategies/public`.
- Утечка `str(exc)`/`{exc}` в detail (много мест primary:772,1360,1142 и т.п.).
- Cookie без `Secure` по умолчанию (`SESSION_HTTPS_ONLY` по умолчанию false); SameSite=lax.
- CMSC debit не атомарен/двойной учёт: `add_wallet_credits(email,-price)` без ledger + `record_payment` после `purchase_plugin` (race).
- `trial=True` в `/api/strategies/activate` — бесплатная активация платной стратегии.
- Глобальные синглтоны без изоляции пользователей: `risk_manager`, `bot`, `strategy_manager`, `_copy_trading_state`, `_payout_settings`; нет singleFlight у BotRuntime (возможен двойной поток на start/resume).
- `/api/bot/simulate` принимает неограниченные `market_data`/`ai_stream` (memory DoS).
- `/auth/telegram/callback` (B:279) объявлен ПОСЛЕ `/auth/{provider}/callback` (B:212) → перекрывается динамическим роутом.

### Низко/инфо
- Два определения `/health` (router + явный @app.get) — избыточность маршрута (B:58/60).
- Логгирование отсутствует (нет basicConfig) несмотря на `CMS_FILE_LOGGING` в render.yaml.
- `/api/admin/login` без rate-limit → брутфорс.
- Legacy SHA-256 вход (password_compat) — держать как временную миграцию.
- Guards-слои дублируются (live_guard, ccxt_guard, execution_gateway) — defense-in-depth, ок.

### Сильные стороны backend
fail-closed kill-switch (`global_kill_switch=True` по умолчанию), `ccxt_guard` глобальный, параметризованный SQL (SQLAlchemy, без инъекций), scrypt-хэши, нет eval/exec/subprocess, allowlist пар/бирж, sanitized 500-handler в B.

## 3. FRONTEND / статика / шаблоны

### HIGH — XSS (неэкранированные innerHTML с пользовательскими/API-данными)
- `dashboard.html:166` — чат: и сообщение юзера, и ответ `/api/chat` вставляются без esc.
- `demo.html:148,152,160,246`, `strategies.html:146-228`, `testing.html:96-111`, `bot_management.html:452-616` (сигналы/стакан/списки стратегий), `arbitrage.html:219,250`, `admin.html:522-523` (stored XSS: site_name/support_contact из админских настроек).
- Мёртвые `cms_sections.js:65-182`, `market_live.js:12`, `market_terminal.js:35`, `market_terminal_patch.js:18,21` — первые же активации дадут XSS, если не esc.
- Чистые/рекомендованные места: `api_render.js` (ApiUI.esc), marketplace, wallet, admin feed — esc используется.

### MEDIUM
- Дубли `static/` ↔ `frontend/` с РАСХОДИМОЙ версией CSS (в B живая `static/`, фронтенд-копия мёртвая; в A наоборот mount на `frontend/`, `static/` отстаёт и в нём нет `market_terminal_patch.js` → при смене mount — 404).
- Мусор: `frontend/Untitled-1`, `frontend/pages/*`, `frontend/index.html` (A).
- Мёртвый `settings.html` (B: не рендерится), мёртвые JS (cms_sections/market_live/terminal/patch не подключены ни в одном шаблоне), `install.html` (A).
- `testing.html:#test-chart` без `trading_chart.js` (график не инициализируется); `testing.html:125` шлёт `&limit=200`, которого нет в роуте (игнорируется).
- CDN-зависимость `lightweight-charts@4.1.1` (base.html:11) — при недоступности CDN IIFE падают.
- Нет favicon; нет meta description/og/twitter.
- `market_live.css` без @media, фикс. высота 480px.
- Слабые умолчания сессии (см. backend SECRET_KEY/SESSION_HTTPS_ONLY).
- Forms (login/register/forgot/admin) без CSRF-токена тела.
- `user-scalable=no` в viewport (доступность).

### Хорошо
- Все fetch→роуты сверены: пути и методы БЕЗ расхождений; `bot_management:173` (trading_test url_path_for) — не поломка; `template_url_for` shim корректен.

## 4. Тесты / CI / деплой

### Тесты
- 82 теста в tests/, в текущем окружении 73 passed / 9 failed. Причины падений: mismatch окружения (installed fastapi 0.141.1 / pydantic 2.13.4 vs requirements 0.109.2 / 2.6.4) + `backend/tests/` (8 тестов) не попадают в `pytest tests` (CI их НЕ исполняет).
- НЕ покрыты тестами: manual trading, wallet, marketplace, strategy generator, bot runtime, arbitrage (в бэкенде B есть arbitrage-роуты; в A — нет), полный auth-flow.

### CI
- `cms-smoke.yml` — curl --fail на `/health`/`/ready` ПАДЁТ для A (health не смонтирован); не соедenen шаги `checkout@v5/setup-python@v6` vs `ci.yml` (v4/v5).
- Линта нет; pytest в prod-requirements.

### Деплой
| Файл | Статус |
|---|---|
| Fly/Render/Railway (healthcheckPath /health) | 🟠 для A сломано (нет /health); для B — ок (health смонтирован) |
| netlify.toml + `netlify/functions/api.py` | 🔴 требует `mangum`, КОТОРОГО нет в requirements |
| vercel.json (@vercel/python main.py) | 🔴 нет mangum/handler — вероятно нерабочий |
| Dockerfile / compose / Procfile / nixpacks | ✅ рабочие (uvicorn backend.main:app) |
| render.yaml | ок (SECRET_KEY generateValue) + мусор `render .yaml` |

### Документация
- README документирует НЕсуществующие `/api/exchange/connect|status|balance`, `/api/trading/order` (дрейф).
- DEPLOYMENT.md говорит, что `GET /` — health; конфликтует с деплой-файлами (/health).
- PROJECT_STATUS/AUTOPILOT/MISSING_FEATURES честно помечают Wallet/Marketplace как непроверенные.

## 5. RUNTIME (живой сервер B)

- `ps` под uuid не виден в контейнере, но `uvicorn` отвечает: `/health`=200, `/ready`=200, `/`=200.
- В логе `INFO`-записи без ошибок; единственный `502 Bad Gateway` на `GET /api/market/history` (внешний fetch к бирже — недетерминированная сеть).
- Статика отдаётся (`/static/api_render.js` 304). API панели отвечают (bot/risk/admin/shadow — 200).
- БД: `cms_core.db` 344 КБ (рабочая), `cms_v12.db` 13.1 МБ; в `backend/` две нулевые заглушки `cms_core.db`/`cms_v12.db` (0 байт, игнорируются git) — кандидаты на удаление.

---

## 6. Приоритетный план (НЕ выполнялся, только рекомендации)

1. CRIT: убрать/закрыть `POST /login/dev-admin-bypass` (или жёстко за APP_ENV=production).
2. CRIT: починить честность `/api/trading/manual` — либо реальный gate-ордер (`submit_real_order(executor,…)`), либо явный статус «demo/simulated», не «executed».
3. HIGH: глобальная обработка 500 (в A) + не возвращать `str(exc)`.
4. HIGH: сквозной CSRF на все POST/формы (double-submit) + обязательный SECRET_KEY + SESSION_HTTPS_ONLY=true.
5. HIGH: прокинуть `ApiUI.esc`/`textContent` во все innerHTML-места frontend (чаты, demo, strategies, testing, bot, arbitrage, admin-настройки, мёртвые JS).
6. MED: уничтожить дубли static/frontend (одна точка монтирования), вычистить мёртвый код/мусор.
7. MED: подключить rate-limit, разнести синглтоны по пользователям, singleFlight бота, атомарный CMSC debit.
8. MED: добавить mangum или убрать serverless-конфиги; синхронизировать requirements (fastapi/pydantic) с окружением; привод `backend/tests/` в `pytest tests`; lint в CI.
9. LOW: чистка `.l2s.tmp_*`, `render .yaml`, пустых db-заглушек, favicon/meta, README-drift.

Итог: код торгового терминала в B работает и отвечает; инфраструктура безопасности и часть деплой-контрактов требуют доработки до «production-ready». Изменения не вносились.