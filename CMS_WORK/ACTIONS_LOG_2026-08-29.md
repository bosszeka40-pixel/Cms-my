# LOG ДЕЙСТВИЙ 2026-08-29 (по файлам)

Сессия: единый красивый рендер API-панелей через модуль ApiUI + git.

## 1. Одобренные пользователем задачи
- Привести к красивому единообразному отображению (карточки, таблицы, бейджи, гейджи) панели API-данных на страницах.
- Только `templates/*.html` и `static/*`; `backend/*.py` и системные файлы не трогать.
- Отвечать на русском.
- В конце: записать всё в `CMS_WORK/` по файлам и сохранить на GitHub.

## 2. Новые файлы

### static/api_render.js (создан, `window.ApiUI`)
- `esc`, `num`/`num6`, `pct`, `signColor`, `time` (ISO и мс-таймстампы).
- `badge(text, tone)` — тоны ok/bad/warn/info/flat.
- `formatValue` — числа (моно), % с цветом, boolean/on/off → бейджи.
- `kv`/`kvRow`/`pretty` — KV-списки с русскими подписями (словарь LABELS), вложенные объекты — карточки.
- `statGrid(stats)` — карточки статистики (label, value, sub, color).
- `gauge(value, max, label, warn)` — прогресс-бар с цветовой индикацией.
- `table(headers, rows)` + ячейки `cellNum/cellColored/cellPct/cellTime`.

### static/style.css (дополнен в конец)
- `.api-kv`, `.api-stat-grid`, `.api-stat(-label/-value/-sub)`, `.api-table`, `.api-progress`, `.api-pill`, `.api-chip`, `.api-feedtime`, медиа-правило <640px. Используют существующие CSS-переменные (`--bg-tertiary`, `--border`, `--success`, `--danger`, `--warning`, `--primary`, `--accent`, `--font-mono`).

## 3. Изменённые шаблоны (фрагменты логики рендера)

### templates/bot_management.html
- Подключён `api_render.js` в `{% block scripts %}`.
- `loadBotBrain`: стат-карточки (действия/история в памяти) + карточки истории.
- `loadBotConfig`: бейдж стратегии + стат-grid комиссия/плечо/риск + KV-карточка конфига (pretty-подписи).
- `loadBotMemory`: стат-grid сделки/средний P/L/винрейт + chips стратегий + карточки лучшей/худшей сделки.
- `loadGenStatus`: стат-grid генерации + сводка + таблица лога с цветной ячейкой.

### templates/manual_trading.html
- Подключён `api_render.js`.
- `submitManualTrade`: стат-grid (статус-бейдж executed/rejected, комиссия, баланс, ID ордера) + `errBox`.
- `submitStrategyTest`: бейдж направления + чипы стратегии/пары + стат-grid P/L/балансы.
- `execStrategy`: бейдж сигнала + chips стратегии/плеча + стат-grid P/L/баланс/комиссия.
- `loadNews`: карточки новостей (пилл источника, время, заголовок-ссылка, clamp 2 строки).
- `loadTrending`: таблица «Стратегия · Доходность/мес · Винрейт · Сделок · Просадка · Sharpe».
- `loadListings`: карточки листингов (имя, бейдж цены/бесплатно, описание, чипы).
- `loadExchanges`: пиллы бирж.

### templates/wallet.html
- `loadWalletStatus`: стат-grid «Баланс · Провайдер (бейдж) · Адрес (моно)`.
- `connectWallet`: бейдж «Кошелёк подключён» + KV.

### templates/marketplace.html
- `loadMarketInfo`: бейджи пары/биржи + таблица performance + карточки публичных стратегий (имя, цена-бейдж, описание, чипы тип/плечо/триал).

### templates/demo.html
- `loadDemoStatus`: стат-grid «Режим (бейдж DEMO/LIVE) · Баланс · Сделок · P/L» (цвета signColor); контейнер `demo-status-box` увеличен.

### templates/admin.html
- `loadRiskStatus`: стат-grid дневного P/L/пика/лимитов + `gauge` скора.
- `calcRisk`: бейдж РАЗРЕШЕНО/ЗАПРЕЩЕНО + причина + гейдж `risk_score / max_allowed`.
- `loadShadowStatus`: бейдж потока + стат-grid тиков/сеттлментов/цены/времени.
- Shadow `evaluate`/`settle`/`monitor`: бейджи + KV-карточка сделки / результат / стат-grid.
- `showLiveAudit`: строки-фиды с бейджами ВКЛ/ВЫКЛ, полем kind, chip target, actor и временем.
- `renderLiveBots`: пиллы с бейджем ON/OFF и кнопкой Вкл/Выкл.

## 4. Проверка (Playwright)
- /bot-management, /admin, /manual-trading, /wallet, /marketplace, /demo на 390 и 1280 px: HTTP 200, без pageerror, без overflow; классы ApiUI присутствуют после рендера.

## 5. Git
- `git add` backend/config.yaml, static/style.css, static/api_render.js, все `templates/*`.
- Коммит: `08fd3c4` «feat: unify pretty render of API panels across terminal pages via ApiUI».
- Ветка `jeevgenij-coder-cms` переведена fast-forward на `08fd3c4` (включает 5ae02ce и 08fd3c4) — готова к пушу.
- Push: ЗАБЛОКИРОВАН отсутствием авторизации GitHub на этой машине → см. `GIT_STATUS_2026-08-29.md`.
- CMS_WORK-отчёты не коммитятся (рабочие заметки сессии).