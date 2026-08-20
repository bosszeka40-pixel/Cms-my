#!/usr/bin/env bash
set -e

if python - <<'PY'
import socket
s = socket.socket()
s.settimeout(0.5)
try:
    s.connect(("127.0.0.1", 8000))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
raise SystemExit(0)
PY
then
    exit 0
fi

nohup python run.py > /tmp/cms.log 2>&1 &
echo $! > /tmp/cms.pid
