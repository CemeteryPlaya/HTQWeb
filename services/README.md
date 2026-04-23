# HTQWeb microservices

Each subdirectory under `services/` is an isolated FastAPI microservice. There is **no shared library**. The canonical structure lives in [`_template/`](_template/) and the rules for adding a new service are below.

## Service map

| Service | Port | Domain |
|---|---|---|
| `user` | 8005 | Identity, profile, admin user mgmt, registration, contact requests |
| `hr` | 8006 | Employees, departments, positions, vacancies, applications, time tracking, documents, audit |
| `task` | 8007 | Tasks, projects, calendar, statistics, links, notifications |
| `cms` | 8008 | Items, news, ConferenceConfig |
| `media` | 8009 | File storage (S3 + local), `secure_media_download` with Range |
| `messenger` | 8010 | WebSocket chat, real-time presence |
| `email` | 8011 | OAuth, MTA, crypto, DLP, threads |

`webtransport/` (QUIC signaling proxy) and `sfu/` (Mediasoup) live at the repo root, not under `services/`.

## Anatomy of a service

```
services/<name>/
├── Dockerfile               # multi-stage, builder + runtime
├── entrypoint.sh            # alembic upgrade head → uvicorn
├── requirements.txt
├── pyproject.toml
├── alembic.ini              # if the service owns DB tables
├── .env.example
└── app/
    ├── main.py              # FastAPI app factory + lifespan
    ├── core/
    │   ├── settings.py      # Pydantic BaseSettings
    │   └── health.py        # /health/, /health/ready/
    ├── auth/
    │   ├── dependencies.py  # JWT validate (issuer=user-service)
    │   └── admin_backend.py # sqladmin AuthenticationBackend
    ├── middleware/
    │   └── request_id.py
    ├── db.py                # SQLAlchemy 2.0 async engine + session
    ├── models/              # SQLAlchemy ORM
    ├── schemas/             # Pydantic DTOs
    ├── repositories/        # DB access (optional)
    ├── services/            # Business logic
    ├── api/v1/              # HTTP routes (registered with /api/<name>/v1 prefix)
    ├── admin/               # sqladmin: ModelView per model + create_admin()
    └── workers/             # Dramatiq actors + (optional) APScheduler periodics
```

The web process and the worker process share the same image; docker-compose runs them with different commands:

```yaml
<name>-service:
  build: ./services/<name>
  command: ["/app/entrypoint.sh"]   # uvicorn

<name>-worker:
  build: ./services/<name>
  command: ["dramatiq", "app.workers.actors", "--processes", "2", "--threads", "4"]
```

## Creating a new service

```bash
cp -r services/_template services/<name>
cd services/<name>
# 1. Replace placeholders
grep -rl '__service_name__' . | xargs sed -i "s/__service_name__/<name>/g"
# 2. Set port + schema in .env.example and Dockerfile (ARG SERVICE_PORT)
# 3. Update docker-compose.yml: add <name>-service and <name>-worker blocks
# 4. Update infra/nginx/default.conf: add /api/<name>/ → <name>-service:<port>
```

## Adding a Dramatiq actor

```python
# app/workers/actors.py
import dramatiq
from app.workers import broker  # noqa: F401  ensures broker is set first

@dramatiq.actor
def send_email(payload: dict) -> None:
    ...
```

Enqueue from a route:

```python
from app.workers.actors import send_email
send_email.send({"to": "user@example.com"})
```

## Registering a sqladmin ModelView

```python
# app/admin/views/employee.py
from sqladmin import ModelView
from app.models.employee import Employee

class EmployeeAdmin(ModelView, model=Employee):
    column_list = [Employee.id, Employee.name]
```

```python
# app/admin/__init__.py — inside create_admin()
from app.admin.views.employee import EmployeeAdmin
admin.add_view(EmployeeAdmin)
```

Admin UI is exposed per-service at `/admin/`, and nginx publishes it at `/admin/<name>/`. Auth is the JWT cookie `admin_session` issued by `user-service` for users with `is_admin: true`.

## Database

All services share one PostgreSQL instance through PgBouncer, with one schema per service (`auth`, `hr`, `tasks`, `cms`, `media`, `messenger`, `email`). The schema is set in each service's `app/db.py` via `connect_args.server_settings.search_path`.

Adoption strategy for tables already created by Django (during migration):

1. Mirror existing tables 1:1 in `app/models/`.
2. `alembic revision --autogenerate -m "initial"` should produce an empty migration.
3. `alembic stamp head` against the live database — no recreation, no data loss.
4. From here on, normal Alembic migrations apply.
