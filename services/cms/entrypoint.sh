#!/bin/sh
# Default web entrypoint: run Alembic migrations (if any) then launch uvicorn.
# Worker processes use a different command (see docker-compose.yml).

set -e

if [ -f alembic.ini ]; then
  alembic upgrade head || echo "alembic upgrade failed — continuing"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${SERVICE_PORT:-8001}"
