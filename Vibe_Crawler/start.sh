#!/usr/bin/env bash
set -euo pipefail

if [ -d "/app/Vibe_Crawler" ]; then
  cd /app/Vibe_Crawler
else
  cd "$(dirname "$0")"
fi

mkdir -p artifacts/reports artifacts/screenshots webapp/jobs

if [ "${INSTALL_PLAYWRIGHT_AT_STARTUP:-0}" = "1" ]; then
  python3 -m playwright install chromium
fi

exec python3 -m uvicorn webapp.app:app --host "${HOST:-0.0.0.0}" --port "${PORT:-10000}"
