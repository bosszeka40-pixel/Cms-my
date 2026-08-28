# План деплоя — 26.08.2026

## Вариант A — Cloudflared Tunnel (рекомендуется)
```bash
# 1. Установка (уже сделано)
# cloudflared уже в /usr/local/bin/cloudflared

# 2. Запуск сервера
cd /root/Documents/Codex/2026-08-25/500/Cms-my
source .venv/bin/activate
python run.py &

# 3. Запуск туннеля
cloudflared tunnel --url http://127.0.0.1:8000
# Вернёт URL вида: https://random-name.trycloudflare.com
```

## Вариант B — Открытие порта (если есть доступ к файрволу)
```bash
# Для Oracle Cloud:
# Добавить правило Security List: Ingress, TCP 8000, Source 0.0.0.0/0
```

## Вариант C — Деплой на Vercel/Render/Railway
- В репозитории уже есть `render.yaml`, `railway.toml`, `vercel.json`
- Нужен GitHub push → автоматический деплой

## GitHub Push
```bash
# Нужно авторизоваться как bosszeka40-pixel:
gh auth logout
gh auth login --hostname github.com --git-protocol https --web

# Или через token:
git remote set-url origin https://<TOKEN>@github.com/bosszeka40-pixel/Cms-my.git
git push origin main
```
