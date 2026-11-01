#!/usr/bin/env bash
# Runs web + worker + frontend concurrently. Ctrl-C kills all.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
trap 'kill 0' SIGINT SIGTERM

(cd "$ROOT/backend" && "$ROOT/.venv/bin/uvicorn" prism.main:app --reload --port 8000) &
(cd "$ROOT/backend" && "$ROOT/.venv/bin/python" -m prism.worker) &
(cd "$ROOT/frontend" && npm run dev) &

wait
