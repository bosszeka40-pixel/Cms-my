# Legacy / остаточный код — проверять перед удалением

Правило: ничего не удалять только потому, что код выглядит старым. Сначала найти все ссылки, проверить runtime/тесты и только после этого переносить или удалять.

## На проверке

### `backend/main.py`
- `HFTSimulatePayload` — **CANDIDATE**. Похоже на тестовый/simulation API-контур. Не удалять до проверки всех `/api/bot/simulate` вызовов из frontend/tests.
- `DEV_ADMIN_BYPASS_ENABLED` + `/login/dev-admin-bypass` — **LEGACY/DEV**. Оставить для текущего development flow; production уже отключает его. Удалять только после готового installer/admin login.
- `forgot_password_submit` — **CANDIDATE**. Сейчас возвращает сообщение без фактической отправки письма. Проверить UI/ожидаемое поведение перед заменой.
- inline exchange connection в `/marketplace` — **CANDIDATE FOR CONSOLIDATION**. Есть отдельный exchange service; сначала сравнить ответственность и вызовы, затем перенести общий код в один сервис.

## Принцип очистки
1. Найти ссылки на код.
2. Определить, нужен ли он для live CMS, тестов или только legacy.
3. Если нужен в другом модуле — перенести без изменения поведения.
4. Если не нужен — удалить отдельным коммитом.
5. После каждого удаления запускать regression tests и обновлять `PROJECT_STATUS.md`.

Статусы: `CANDIDATE` → `VERIFY` → `MOVED` или `REMOVED`.
