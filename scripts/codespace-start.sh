#!/usr/bin/env bash
set -e

if python - <<'PY'
import urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
except Exception:
    raise SystemExit(1)
raise SystemExit(0)
PY
then
    exit 0
fi

nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/cms.log 2>&1 &
echo $! > /tmp/cms.pid
