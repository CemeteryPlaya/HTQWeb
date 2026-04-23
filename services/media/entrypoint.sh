#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="media-service"
SERVICE_ENV="${SERVICE_ENV:-development}"
APP_PORT="${SERVICE_PORT:-8009}"

echo "[${SERVICE_NAME}] env=${SERVICE_ENV} — running alembic upgrade head"

if ! PYTHONPATH=/app alembic upgrade head; then
    echo "[${SERVICE_NAME}] ERROR: alembic upgrade failed."
    exit 1
fi

echo "[${SERVICE_NAME}] migrations OK — starting uvicorn on :${APP_PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT}"
