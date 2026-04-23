# ─── Backend (Django + Daphne ASGI) ─────────────────────────────────────────
# Multi-stage: build dependencies, then copy into slim runtime image
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# System dependencies for building Python packages (psycopg, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev libpq-dev libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt gunicorn

# ─── Runtime stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime libraries only (no compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libjpeg62-turbo zlib1g curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Remove dev artifacts that might have leaked through .dockerignore
RUN rm -rf __pycache__ *.sqlite3 *.log media/ staticfiles/ \
    scripts/dev/ debug_*.py debug_*.txt probe_*.py verify_system.py \
    api_*.json tasks_output.json run_local.ps1 test_deadline.py

# collectstatic without DB connection
RUN mkdir -p /app/staticfiles && \
    DJANGO_SECRET_KEY=build-placeholder DEBUG=False \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "HTQWeb.asgi:application"]
