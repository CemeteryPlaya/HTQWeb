#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Backend entrypoint — runs before the main process (CMD).
# 1. Wait for database to become reachable
# 2. Run Django migrations
# 3. Collect static files
# 4. Hand off to CMD (daphne, gunicorn, etc.)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Wait for database ──
DB_HOST="${DB_HOST:-pgbouncer}"
DB_PORT="${DB_PORT:-5432}"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "[entrypoint] Waiting for database at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 $MAX_RETRIES); do
    if python -c "
import socket, sys
try:
    s = socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=3)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "[entrypoint] Database is reachable (attempt ${i}/${MAX_RETRIES})"
        break
    fi

    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "[entrypoint] ERROR: Database at ${DB_HOST}:${DB_PORT} not reachable after ${MAX_RETRIES} attempts"
        exit 1
    fi

    echo "[entrypoint] Database not ready yet (attempt ${i}/${MAX_RETRIES}), retrying in ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done

# ── Run migrations ──
echo "[entrypoint] Running Django migrations..."
python manage.py migrate --noinput

# ── Collect static files ──
echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput

echo "[entrypoint] Starting application: $@"

# ── Hand off to CMD ──
exec "$@"
