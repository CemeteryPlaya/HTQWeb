FROM python:3.12-slim

WORKDIR /app

# System dependencies (gcc for some C extensions, curl for healthcheck)
# libpq-dev needed for asyncpg compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Idempotent entrypoint: runs migrations, then uvicorn (with dev recovery hint)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:${SERVICE_PORT:-8006}/health/ || exit 1

EXPOSE 8006

CMD ["/app/entrypoint.sh"]
