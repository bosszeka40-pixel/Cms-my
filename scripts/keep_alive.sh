#!/usr/bin/env bash
# Runs the app in a loop, auto-restarting it if it crashes.
# Usage: nohup bash scripts/keep_alive.sh > /dev/null 2>&1 & disown
set -u
cd "$(dirname "$0")/.."

LOG_FILE="keep_alive.log"
PID_FILE="keep_alive.pid"

echo $$ > "$PID_FILE"

while true; do
    echo "$(date '+%F %T') starting app" >> "$LOG_FILE"
    python run.py >> "$LOG_FILE" 2>&1
    exit_code=$?
    echo "$(date '+%F %T') app exited with code $exit_code, restarting in 5s" >> "$LOG_FILE"
    sleep 5
done
