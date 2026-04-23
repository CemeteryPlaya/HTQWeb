# Run Django locally with DB pointing to the Docker postgres container.
# Usage: .\run_local.ps1
# Prerequisites: docker compose up -d db

if (-not $env:DB_ENGINE) { $env:DB_ENGINE = "django.db.backends.postgresql" }
if (-not $env:DB_NAME) { $env:DB_NAME = "htqweb" }
if (-not $env:DB_USER) { $env:DB_USER = "htqweb" }
if (-not $env:DB_PASSWORD) { $env:DB_PASSWORD = "change-me" }
if (-not $env:DB_HOST) { $env:DB_HOST = "localhost" }
if (-not $env:DB_PORT) {
    if ($env:DB_HOST_PORT) {
        $env:DB_PORT = $env:DB_HOST_PORT
    } else {
        $env:DB_PORT = "55432"
    }
}

python manage.py runserver
