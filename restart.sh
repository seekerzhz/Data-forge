#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${DATAFORGE_HOST:-127.0.0.1}"
PORT="${DATAFORGE_PORT:-8000}"
UVICORN_BIN=".venv/bin/uvicorn"

if [ ! -x "$UVICORN_BIN" ] && [ -x "venv/bin/uvicorn" ]; then
  UVICORN_BIN="venv/bin/uvicorn"
fi

pkill -f "uvicorn webapp:app" || true

nohup "$UVICORN_BIN" webapp:app \
  --host "$HOST" \
  --port "$PORT" \
  > log.txt 2>&1 &

echo "DataForge started on http://${HOST}:${PORT}"
