# План: продолжение big-bang перехода HTQWeb с Django на FastAPI

> Полный исходный план: `C:\Users\User\.claude\plans\piped-gliding-perlis.md`
> Этот файл — **только то, что осталось сделать** на момент паузы 2026-04-23.

## Статус по фазам

| Фаза | Статус | Комментарий |
|---|---|---|
| Phase 0 — Cleanup | ✅ done | Мусорные файлы удалены |
| Phase 1 — Infra reorg | ✅ done | `infra/{nginx,db,certs}/`, `backend/Dockerfile`, dev-скрипты в `backend/scripts/dev/` |
| Phase 2 — Template alignment | ✅ done | `_template/` приведён к канону (lifespan, sqladmin, dramatiq, apscheduler) |
| Phase 3.1 — user-service | ✅ done | `routers/`→`api/v1/`, `Item` модель/CRUD, admin (User/PendingRegistration/Item), workers (email_confirmation_send + cleanup_stale_pending_registrations) |
| Phase 3.7 — hr/task admin+workers | ✅ done | hr: 13 ModelView + audit_log_compaction + vacancy_application_notify. task: 10 ModelView + task_deadline_reminder + notification_dispatch. CORS убран из task/main.py |
| **Phase 3.2 — cms-service** | 🟡 **in progress (~15%)** | См. ниже |
| Phase 3.3 — media-service | ⬜ pending | |
| Phase 3.6 — port backend/tasks/ | ⬜ pending | |
| Phase 3.4 — messenger-service | ⬜ pending | |
| Phase 3.5 — email-service | ⬜ pending | |
| Phase 4 — Cutover (frontend, nginx, compose, удаление Django) | ⬜ pending | |

---

## Phase 3.2 — services/cms/ (продолжить отсюда)

### Уже сделано
- `cp -r services/_template services/cms`
- `services/cms/.env.example`: `SERVICE_NAME=cms`, `SERVICE_PORT=8008`, `DB_SCHEMA=cms`, `OTEL_SERVICE_NAME=cms`
- `services/cms/pyproject.toml`: `name = "cms-service"`

### Прочитанные источники (не нужно перечитывать)
- `backend/media_manager/models.py` — модели `News` и `ContactRequest` (см. ниже схему)
- `backend/media_manager/views.py` — ViewSets `NewsViewSet` (с action `translate`), `ContactRequestViewSet`
- `backend/mainView/views.py` — `ConferenceConfigView` (статический JSON, без таблицы)

### Осталось сделать

**1. Заменить placeholder'ы в шаблонных файлах:**
- `services/cms/app/main.py`: `__service_name__` → `cms`, `__service_description__` → `CMS-контент: новости, contact-requests, конференция`
- `services/cms/app/api/v1/example.py` — удалить или переименовать в `news.py`/`contact_requests.py`/`conference.py`

**2. Модели `services/cms/app/models/`:**

`news.py`:
```python
# News (зеркало backend/media_manager/models.py:5-20)
# Поля: id, title (String 300), slug (String 320, unique), summary (Text),
#       content (Text), image (String 500, nullable — путь в media-service),
#       category (String 100, indexed), published (Bool, indexed),
#       published_at (DateTime, nullable, indexed), created_at (auto)
# db_table: cms.news (был mainView_news)
```

`contact_request.py`:
```python
# ContactRequest (зеркало backend/media_manager/models.py:23-44)
# Поля: id, first_name (String 150), last_name (String 150), email (String 254),
#       message (Text), handled (Bool, indexed), replied_at (DateTime, indexed),
#       replied_by_id (Integer, nullable — FK на users.id в auth-схеме, без constraint),
#       reply_message (Text), created_at (auto)
```

Не забыть обновить `services/cms/app/models/__init__.py` с экспортом обоих + `Base`.

**3. Endpoints `services/cms/app/api/v1/`:**

- `news.py` — CRUD `/api/cms/v1/news/`:
  - `GET /` — публичный список published=True
  - `POST /` — admin-only (require `is_admin`)
  - `GET /{id}` — публичный
  - `PATCH /{id}`, `DELETE /{id}` — admin
  - `POST /{id}/translate` — зеркало `NewsViewSet.translate` (вызов внешнего translation API; пока stub возвращает оригинал)
- `contact_requests.py`:
  - `POST /api/cms/v1/contact-requests/` — публичный (rate-limit через `slowapi`, например 3/мин на IP)
  - `GET /api/cms/v1/contact-requests/` — admin list (with `?handled=false` filter)
  - `PATCH /{id}` — admin (handle + reply)
- `conference.py`:
  - `GET /api/cms/v1/conference/config` — статический JSON. Источник: `Settings.conference_config` (Pydantic model в `core/settings.py`) или отдельный YAML-файл в `app/data/conference.yaml`. **Без таблицы.**

Зарегистрировать роутеры в `services/cms/app/main.py` под префиксом `/api/cms/v1`.

**4. Admin `services/cms/app/admin/`:**
- Скопировать `services/user/app/auth/admin_backend.py` → `services/cms/app/auth/admin_backend.py` (он уже в `_template/`, проверить)
- `views/__init__.py`: 2 ModelView:
  - `NewsAdmin`: column_list = id/title/category/published/published_at/created_at; searchable=title; sort by created_at desc
  - `ContactRequestAdmin`: column_list = id/email/first_name/last_name/handled/created_at; sort by created_at desc; searchable=email
- `__init__.py`: `create_admin(app, engine)` регистрирует обе

**5. Workers `services/cms/app/workers/`:**
- `__init__.py`: RedisBroker setup (как в `services/task/app/workers/__init__.py`)
- `actors.py`: пока пусто (или actor `notify_admins_on_contact_request` — вызывается из POST /contact-requests/)
- `scheduler.py`:
  - `news_scheduled_publish`: APScheduler cron `minute='*'`. SQL:
    ```python
    UPDATE cms.news
       SET published = TRUE
     WHERE published = FALSE
       AND published_at IS NOT NULL
       AND published_at <= now()
    ```

**6. Requirements `services/cms/requirements.txt`:**
- Добавить (как в task/hr/user): `sqladmin==0.20.1`, `itsdangerous==2.2.0`, `dramatiq[redis,watch]==1.17.1`, `apscheduler==3.10.4`, `slowapi==0.1.9`

**7. Smoke-тест:**
- `cd services/cms && uvicorn app.main:app --port 8008` → проверить `/health/`, `/docs`, `/admin/`

---

## Phase 3.3 — services/media/

`cp -r services/_template services/media`, `SERVICE_PORT=8009`, `DB_SCHEMA=media`.

### Структура
- `app/storage.py` — абстракция:
  - `S3Storage` через `aioboto3` (для AWS/MinIO)
  - `LocalStorage` через `aiofiles` (когда `STORAGE_BACKEND=local`)
  - Перенос логики из `backend/HTQWeb/storage_backends.py` (`PublicMediaStorage`, `PrivateMediaStorage`)
- `app/models/file_metadata.py` — таблица для отслеживания загруженных файлов (id, path, owner_id, size, mime, created_at)
- `app/api/v1/files.py`:
  - `POST /api/media/v1/upload` — multipart, возвращает `{file_id, url}`
  - `GET /api/media/v1/download/{path:path}` — порт `secure_media_download` из `backend/media_manager/file_views.py:60-129`:
    - HTTP Range (206) через `StreamingResponse` + custom byte-range handler
    - ETag + 304 Not Modified
    - 8KB chunks
    - Path-traversal защита (нормализация + проверка что resolved path внутри base_dir)
  - `POST /api/media/v1/presign` — presigned URL для прямой S3-загрузки
- `app/admin/` — file browser ModelView (читает из `file_metadata`)
- `app/workers/`:
  - actor `generate_thumbnail` (Pillow, по событию upload)
  - APScheduler `cleanup_orphan_files` (еженедельно, сравнивает S3-листинг с `file_metadata`)
- Требования: добавить `aioboto3`, `aiofiles`, `Pillow`, плюс admin/workers стек

### Volume mapping
В `docker-compose.yml`: `./backend/media:/app/data/media` для local fallback. Avatars и `news_images/` остаются в этом volume.

---

## Phase 3.6 — Перенести backend/tasks/ → services/task/

### Что уже есть в task-service
- Модели: `task.py`, `activity.py`, `attachment.py`, `comment.py`, `label.py`, `link.py`, `notification.py`, `sequence.py`, `version.py`, `base.py` (10 файлов)
- Admin views: 10 штук
- Workers: `task_deadline_reminder`, `notification_dispatch`

### Чего не хватает
- Endpoints из `backend/tasks/views/` (12 ViewSets) → `services/task/app/api/v1/`:
  - tasks, comments, attachments, links, activity, labels, versions, notifications, sequences, **calendar**, **statistics** + ещё 1 (свериться с `backend/tasks/views/__init__.py`)
- **Возможно недостающие модели**: `Project`, `ProductionDay` (для календарного расчёта дедлайнов в `backend/scripts/dev/test_deadline.py`). Сверить с `backend/tasks/models.py`. `ProductionDay` уже есть в admin → значит модель тоже есть, но проверить `Project`
- `app/services/calendar.py` — порт логики «рабочие/выходные дни через `ProductionDay`» (O(1) через `working_days_since_epoch`)

### Контракт
- Frontend `frontend/src/api/tasks.ts` и `frontend/src/api/calendar.ts` уже целятся в `/api/tasks/v1` — сохранить response shape как в Django ViewSets

---

## Phase 3.4 — services/messenger/

`cp -r services/_template services/messenger`, `SERVICE_PORT=8010`, `DB_SCHEMA=messenger`.

### Стек
- WebSocket: **нативный FastAPI** (`@router.websocket`), не `python-socketio`
- Redis pub/sub: `redis.asyncio.Redis.pubsub()` (заменяет Django Channels)
- DDD-структура 1:1 из `backend/messenger/`:
  - `app/domain/models.py` — 6 моделей: `ChatUserReplica`, `ChatRoom`, `ChatMembership`, `EncryptedMessage`, `AuthKeyBundle`, `ChatAttachment`
  - `app/infrastructure/` — repositories, ltree_fields, Redis pubsub bridge
  - `app/application/` — use-cases (отправка/прочтение/typing)
  - `app/presentation/` или `app/api/v1/ws.py` — WS consumer (порт `backend/messenger/presentation/consumers.py`)

### Маршруты
- WS: `/ws/messenger/chat/{room_id}/` (зеркало `routing.py:9-10`)
- REST: `/api/messenger/v1/rooms/`, `/messages/`, `/attachments/`
- **Протокол сообщений не менять** (зеркало `consumers.py:7-16`) — фронт не ломать

### ChatAttachment
- Локальный storage внутри messenger-service (свой S3 prefix `messenger/`), без round-trip в media-service

### Admin: 6 ModelView
### Workers
- `dispatch_push_notification` (FCM/APNS — пока noop с логом, если нет ключей)
- APScheduler `archive_old_messages` (ежедневно, msg старше 90д → cold storage)
- `cleanup_presence` (Redis TTL по user_id)

### Зависимости
- `websockets` уже идёт с uvicorn[standard]
- `sqlalchemy-utils` для `LtreeType` (или собственный `ltree_fields.py`)

---

## Phase 3.5 — services/email/

`cp -r services/_template services/email`, `SERVICE_PORT=8011`, `DB_SCHEMA=email`.

### 5 тяжёлых модулей (порт из backend/internal_email/)
- `crypto.py` → `app/services/crypto.py` — AES-256-GCM через `cryptography.hazmat`. **НЕ логировать plaintext**
- `dlp_scanner.py` → `app/services/dlp.py`
- `mta_connector.py` → `app/services/mta.py` — SMTP (`aiosmtplib`) + IMAP (`aioimaplib`)
- `oauth.py` → `app/services/oauth.py` — Google Workspace + Microsoft 365
- `services.py` → `app/services/email_service.py`

### Модели (4 шт., из `backend/internal_email/models.py`)
`EmailMessage`, `EmailRecipientStatus`, `EmailAttachment`, `EmailOAuthToken`

### Endpoints (10 шт.)
- `inbox`, `sent`, `drafts`, `trash` (GET/POST)
- `send`, `draft` (POST)
- `read/{pk}` (GET)
- `oauth/init`, `oauth/callback`, `oauth/status`, `oauth/disconnect`

### Admin: 4 ModelView
- **Маскирование OAuth tokens** через `column_formatters`

### Workers
- APScheduler `mta_inbound_poll` (каждые 60с)
- APScheduler `oauth_token_refresh` (каждые 30 мин)
- Dramatiq actor `dlp_scan_attachment` (по upload)
- Dramatiq actor `send_email` (retry с exponential backoff через middleware `Retries`)

### Зависимости
`aiosmtplib`, `aioimaplib`, `cryptography`, `httpx` (для OAuth)

---

## Phase 4 — Cutover (big-bang релиз)

### 4.1. Frontend API client refactor
- `frontend/src/api/hr.ts` → `/api/hr/v1` ✅ уже
- `frontend/src/api/tasks.ts`, `calendar.ts` → `/api/tasks/v1`
- Создать: `frontend/src/api/{users,cms,media,messenger,email}.ts`
- `frontend/src/lib/auth/` JWT эндпоинт → `/api/users/v1/token/`
- `frontend/src/hooks/useActiveProfile.ts` → `/api/users/v1/profile/me`
- `frontend/src/api/fileManager.ts` → `/api/media/v1/*`
- `frontend/src/services/emailService.ts` → `/api/email/v1/*` (заодно перенести в `frontend/src/api/email.ts`)
- `frontend/src/features/messenger/` → новый WS URL и REST префикс

### 4.2. Nginx upstream-конфиг (`infra/nginx/default.conf`)
```
/api/users/      → user-service:8005
/api/hr/         → hr-service:8006
/api/tasks/      → task-service:8007
/api/cms/        → cms-service:8008
/api/media/      → media-service:8009
/api/messenger/  → messenger-service:8010 (включая /ws/messenger/)
/api/email/      → email-service:8011
/admin/<service>/→ соответствующий сервис на /admin/
/ws/sfu/         → sfu:4443  (без изменений)
```

### 4.3. docker-compose.yml финал
- Удалить блок `backend:` (Django)
- Добавить: `cms-service`, `cms-worker`, `media-service`, `media-worker`, `messenger-service`, `messenger-worker`, `email-service`, `email-worker`
- Добавить worker-блоки для существующих: `user-worker`, `hr-worker`, `task-worker`
- Поправить `nginx.depends_on`
- Поправить `webtransport` context на `./webtransport`

### 4.4. Удалить Django
После validation:
- `backend/HTQWeb/`, `manage.py`, `requirements.txt`, `entrypoint.sh`
- Django-приложения: `hr/`, `internal_email/`, `mainView/`, `media_manager/`, `messenger/`, `tasks/`
- `backend/webtransport/` (уже перенесено)
- Удалить `backend/` целиком
- Удалить корневой `Dockerfile` (если не перенесён в Phase 1)

### 4.5. Database (Alembic stamp стратегия)
В каждом новом сервисе:
1. `alembic init`
2. Скопировать описание существующих таблиц в `models/` (1:1 с Django)
3. `alembic revision --autogenerate -m "initial"` → должна быть пустая миграция
4. `alembic stamp head` против БД
5. Дальше — нормальные миграции

В конце: удалить `django_migrations` таблицу.

---

## Verification после каждого Track

- Unit-тесты в `services/<X>/tests/`
- `docker compose up <service>-service <service>-worker` локально
- Postman/curl smoke vs Django (response shape должен совпадать)
- Контракт-тест с user-service (JWT validation работает)
- sqladmin доступен по `/admin/` (с auth backend через `admin_session` cookie)

## E2E browser smoke (после Phase 4)
- Регистрация → login → профиль
- Открыть admin для каждого сервиса (`/admin/users/`, `/admin/hr/`, ...)
- HR: создать сотрудника, отдел
- Tasks: создать задачу, проверить календарь
- Messenger: WS отправка/получение
- Email: создать черновик, OAuth callback
- Media: загрузить файл, скачать (с Range), удалить
- Conference (SFU): запустить звонок, WebRTC

---

## Rollback strategy
- Тэг `v1.0-django-final` перед cutover
- Хранить Django docker-image (`htqweb-backend:django-final`)
- nginx upstream через переменную (быстрый switch на `backend:8000`)
- Данные не дублируются (alembic stamp), Django можно вернуть без потерь

## Что осознанно НЕ делается
- Нет `services/_shared/` — каждый сервис самодостаточен
- frontend helper-скрипты не объединяются
- БД одна (PgBouncer), per-service только схемы
- Полное разделение БД (per-service DB) — следующая итерация, не в этом плане

## Открытые вопросы
- Admin auth UX: каждый сервис свой `/admin/` (текущий план) vs единая SPA с табами
- WS стек: нативный FastAPI WS (текущий план) vs `python-socketio`
- API gateway для агрегации OpenAPI: пока нет (каждый сервис свой `/docs`)
- Migration window: 30-60 мин downtime для DB stamp + nginx switch

---

## Технические инварианты (применять в каждом новом сервисе)

- **Lifespan** через `@asynccontextmanager`, не `@app.on_event`
- **CORS** не добавляется в сервисах — унифицируется на nginx
- **JWT**: `JWTAdminAuthBackend` читает cookie `admin_session`, проверяет issuer + claim `is_admin: true`
- **sqladmin**: `Admin(app, engine, base_url="/admin", authentication_backend=JWTAdminAuthBackend(secret_key=settings.jwt_secret))`
- **Dramatiq**: `RedisBroker(url=settings.redis_url)`; импорт `from app.workers import actors as _actors  # noqa: F401` в `main.py` для регистрации брокера
- **APScheduler**: `python -m app.workers.scheduler` отдельным процессом
- **Requirements** для админки/воркеров (одинаково везде):
  ```
  sqladmin==0.20.1
  itsdangerous==2.2.0
  dramatiq[redis,watch]==1.17.1
  apscheduler==3.10.4
  ```
- **DB schema**: каждый сервис имеет свою схему (`auth`, `hr`, `tasks`, `cms`, `media`, `messenger`, `email`), `search_path` выставляется в `connect_args.server_settings`
- **Структура директорий внутри `app/`** строго: `core/`, `auth/`, `middleware/`, `db.py`, `models/`, `schemas/`, `repositories/` (опц.), `services/`, `api/v1/`, `admin/`, `workers/`
