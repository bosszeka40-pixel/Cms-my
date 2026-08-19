# CMS Work Tree

Единая карта рабочих веток CMS. Используется как быстрый вход после потери истории чата.

## Правило закрытия ветки
`UI → JS → API → Router → Service → DB/Exchange → Response → UI → Test → DONE`

После `DONE` ветка не пересматривается без нового подтверждённого теста/ошибки.

## Branches

- [ ] 01 Marketplace / Plugins — IN PROGRESS
  - [x] Backend/plugin model
  - [x] API/routes
  - [x] Frontend/template
  - [x] JS/actions
  - [x] Install/activate/deactivate
  - [ ] CMSC purchase/renewal debit test
  - [ ] Integration test
  - [ ] UI/design
  - [ ] DONE
- [ ] 02 Dashboard
- [ ] 03 Wallet
- [ ] 04 Bot management
- [ ] 05 Settings
- [ ] 06 Admin
- [ ] 07 Login/Register/Social login
- [ ] 08 Market / Candles / Live
- [ ] 09 Exchange connection / Trading
- [ ] 10 Database
- [ ] 11 Installer
- [x] 12 Error logging / server diagnostics — deployment smoke DONE
- [ ] 13 Legacy cleanup

## Working documents
Все рабочие карты, заметки и результаты этой фазы держать только в `CMS_WORK/`.

- `TREE.md` — карта веток
- `CURRENT.md` — текущая функция и полный маршрут
- `DECISIONS.md` — принятые решения, чтобы не повторять обсуждение
- `ERRORS.md` — ошибки тестирования/сервера
- `LEGACY.md` — кандидаты на удаление и результат проверки
- `CHECKLIST.md` — общий контрольный список
