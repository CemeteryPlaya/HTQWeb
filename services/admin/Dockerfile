FROM python:3.12-slim

WORKDIR /app

# Все сервисы монтируются как siblings → /services/<svc>/app
ENV PYTHONPATH=/services/user:/services/hr:/services/task:/services/cms:/services/media:/services/messenger:/services/email

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app

# Дочерние сервисы будут mounted via volumes в compose:
# volumes:
#   - ./services/user:/services/user:ro
#   - ./services/hr:/services/hr:ro
#   ...

EXPOSE 8012
HEALTHCHECK --interval=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8012/health/').read()" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012"]
