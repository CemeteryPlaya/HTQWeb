FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости для Pillow и psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg[binary]

COPY backend/ .

# collectstatic без подключения к БД
RUN mkdir -p /app/staticfiles && \
    DJANGO_SECRET_KEY=build DEBUG=False python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "HTQWeb.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
