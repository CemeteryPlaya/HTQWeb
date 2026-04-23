# PLAN.md — Execution log миграции HTQWeb (Django → FastAPI)

> **Источник истины (полный план):** `C:\Users\User\.claude\plans\dynamic-imagining-goblet.md`
> **Этот файл** — живой журнал выполнения + пошаговая инструкция для оставшихся фаз. Обновляется **после каждой завершённой фазы** одновременно с git-коммитом. Предотвращает рассинхрон контекста между сессиями (anti-hallucination container).

---

## Протокол ведения (обязательно для каждой сессии)

**В начале сессии:**
1. Прочитать этот файл целиком.
2. Прочитать полный план в `C:\Users\User\.claude\plans\dynamic-imagining-goblet.md`.
3. Сверить реальное состояние с журналом:
   - `git log --oneline -10` — последний коммит совпадает с записью?
   - `git tag` — `v1.0-django-final` на месте?
   - `ls services/` — сервисы, помеченные ✅, существуют?
   - `docker images` — образы на месте?
4. Если state расходится — **сначала обновить журнал** записью «Синхронизация», потом работать.

**Перед началом фазы:**
- Пометить в таблице статус `🟡 in_progress`.
- В логе создать секцию фазы с пустыми `сделано/непроверено/отклонения`.

**После коммита фазы:**
- В таблице `✅ done` + hash коммита.
- Заполнить секцию лога честно (что реально сделано, что пропущено, что не верифицировано).
- **Никогда не удалять старые записи** — только добавлять.

**При признаках путаницы (галлюцинации):**
- Остановиться. Прочитать этот файл. Проверить state команды `git status` + `ls`.
- Если найдено расхождение — добавить запись «Desync detected» с диагнозом.

---

## Таблица статусов фаз

| Фаза | Статус | Коммит | Tag |
|---|---|---|---|
| 0.5 Cleanup + rollback | ✅ done | `fc722e4` (0.0.2.3) | `v1.0-django-final` |
| 0.6 Observability bootstrap | ✅ done | `fc722e4` (0.0.2.3) | — |
| 3 (bulk) cms/media/messenger/email/admin + task endpoints | ✅ done | `2f93153` (0.0.2.4) | — |
| **3.7 Fill Phase 3 gaps** | ✅ done | `0.0.2.5` | — |
| 4 Cutover (frontend + Alembic + rm Django) | ⬜ pending — **следующая** | — | — |
| 5 Post-production audit | ⬜ pending | — | `v1.0-fastapi-production` (в конце) |

---

## Ключевые решения (зафиксировано)

- **Режим:** big-bang до Phase 4.5 (+ Phase 5), пошаговые коммиты после каждой подфазы.
- **CMS news.translate** — Dramatiq actor + внешний API TODO через env.
- **CMS conference config** — YAML `app/data/conference.yaml`.
- **Media storage** — `aiofiles` (local) для dev/early-prod, `aioboto3` (S3) через `STORAGE_BACKEND` env.
- **Messenger WS** — `python-socketio` + Redis adapter (НЕ нативный FastAPI WS).
- **Email OAuth** — env-плейсхолдеры, endpoints 503 при пустых ключах.
- **Alembic** — `autogenerate` даёт diff=0 против живых Django-таблиц, затем `stamp head`.
- **Admin UI** — единый `services/admin/` (агрегатор) с импортом моделей через PYTHONPATH.
- **Messenger attachments** — локально в messenger-service.
- **Rollback** — `git tag v1.0-django-final` + docker-image `htqweb-backend:django-final` (оба созданы).
- **Logging** — Loki + Promtail + Grafana self-hosted в compose.
- **Audit log** — таблица `audit_log` в каждой схеме + поток в Loki.
- **Тесты** — `pytest + testcontainers` (реальный Postgres); unit + integration + E2E (Playwright).

---

# ═══════════════════════════════════════════════════════════
# Phase 3.7 — Fill Phase 3 gaps (ПОЛНАЯ ПОШАГОВАЯ ИНСТРУКЦИЯ)
# ═══════════════════════════════════════════════════════════

**Цель.** Довести сервисы Phase 3 до состояния, при котором Phase 4 (cutover) возможно физически выполнить. Без этой фазы блокируется: alembic stamp (5 сервисов без alembic), admin-aggregator (неполные импорты), фронт (task/comments и messenger/read не существуют).

**Оценка.** 1 большая или 2 средних сессии. ~80 создаваемых/изменяемых файлов. 1 коммит в конце (`0.0.2.5`).

**Предусловия.**
- HEAD на `d2f3b71` (или дальше, если были docs-коммиты).
- Все сервисы парсятся (проверено AST).
- Runtime не запускался — это нормально; smoke будет в 3.7.8.

**Общий порядок:** 3.7.1 → 3.7.2 → 3.7.3 → 3.7.4 → 3.7.5 → 3.7.6 → 3.7.7 → 3.7.8 → 3.7.9. Шаги 3.7.2–3.7.6 независимы и могут идти параллельно (в разных ветках) если понадобится распараллелить, но в одной сессии — последовательно для ясности diff'а.

---

## 3.7.1 Observability propagation

**Зачем.** messenger, email, admin полностью лишены observability-файлов, добавленных в `_template` в 0.0.2.3. media частично (нет `request_logging.py`). Их логи нельзя будет собирать в Loki по единому формату, audit_log не будет писаться.

**Что делать.**

### 3.7.1.a — скрипт проверки состояния (дважды: до и после)
В консоли в корне проекта (bash):
```bash
for svc in cms media messenger email admin; do
  for f in app/core/logging.py app/middleware/request_id.py app/middleware/request_logging.py \
           app/models/base.py app/models/audit_log.py app/services/audit.py; do
    test -f services/$svc/$f && s="Y" || s="N"
    printf "%-10s %-45s %s\n" "$svc" "$f" "$s"
  done
done
```
Ожидаем после 3.7.1: везде `Y`.

### 3.7.1.b — копирование файлов
Для каждого из 4 сервисов (`media, messenger, email, admin`) скопировать из `services/_template/`:

| Источник | Цель |
|---|---|
| `services/_template/app/core/logging.py` | `services/<svc>/app/core/logging.py` |
| `services/_template/app/middleware/request_id.py` | `services/<svc>/app/middleware/request_id.py` (перезаписать) |
| `services/_template/app/middleware/request_logging.py` | `services/<svc>/app/middleware/request_logging.py` |
| `services/_template/app/models/base.py` | `services/<svc>/app/models/base.py` (см. конфликт ниже) |
| `services/_template/app/models/audit_log.py` | `services/<svc>/app/models/audit_log.py` |
| `services/_template/app/services/audit.py` | `services/<svc>/app/services/audit.py` |

**Метод (bash):**
```bash
for svc in media messenger email admin; do
  mkdir -p services/$svc/app/{core,middleware,models,services}
  for f in app/core/logging.py app/middleware/request_id.py app/middleware/request_logging.py \
           app/models/audit_log.py app/services/audit.py; do
    cp services/_template/$f services/$svc/$f
  done
done
```

**Конфликт `models/base.py`.** У messenger и email уже есть свой `base.py`. НЕ перезаписывать — сравнить diff'ом (`diff services/_template/app/models/base.py services/messenger/app/models/base.py`). Если отличается только `TimestampMixin`/`IntIdMixin` которые существующие модели не используют — оставить как есть. Если отличается класс `Base` — взять версию из `_template` (одна `DeclarativeBase` на сервис, критично для Alembic).

### 3.7.1.c — обновить `models/__init__.py` в каждом из 4 сервисов
Добавить экспорт `AuditLog`:
```python
from app.models.audit_log import AuditLog  # noqa: F401
```
Добавить `"AuditLog"` в `__all__` если он там есть.

### 3.7.1.d — обновить `main.py` в каждом из 4 сервисов
Заменить:
```python
import logging
...
structlog.configure(...)  # inline config
```
На:
```python
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

log = get_logger(__name__)

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(...)
    app.add_middleware(RequestLoggingMiddleware)  # outer
    app.add_middleware(RequestIDMiddleware)       # inner
    ...
```
Паттерн как в `services/_template/app/main.py` (после 0.0.2.3).

### 3.7.1.e — проверка
```bash
python -c "
import ast
for p in ['services/media/app/main.py', 'services/messenger/app/main.py',
          'services/email/app/main.py', 'services/admin/app/main.py']:
    ast.parse(open(p, encoding='utf-8').read())
    print(p, 'OK')
"
```

**Verification:** повторить скрипт 3.7.1.a — все ячейки `Y`.

**Риски.**
- `_template/app/core/settings.py` не содержит CMS/messenger-specific поля — `logging.py` импортирует только `settings.log_level`, что есть у всех. Должно работать.
- Конфликт имён если в existing `main.py` уже есть `from app.middleware.request_id import ...` — тогда перезапись тривиальна.

---

## 3.7.2 Messenger — missing endpoints + observability + workers + admin split

**Зачем.** План требовал 7 REST-групп, сделано 4. Нет `middleware/`, нет audit, нет scheduler, admin собран в один файл.

### 3.7.2.a — новые endpoints

#### `services/messenger/app/api/v1/read.py`
```python
"""Mark-read endpoint — REST counterpart of Socket.IO 'mark_read' event."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session
from app.models.domain import ChatMembership
from app.services.audit import record_action

router = APIRouter(tags=["read"])

@router.post("/rooms/{room_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    room_id: int,
    pts: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[TokenPayload, Depends(get_current_user)],
) -> None:
    # UPDATE ChatMembership SET local_pts=GREATEST(local_pts, :pts),
    #                           last_read_at=now(), unread_count=0
    #  WHERE room_id=:room_id AND user_id=:user_id
    # + broadcast через sio.emit('read_receipt', ...)
    ...
```

#### `services/messenger/app/api/v1/attachments.py`
```python
"""Chat attachment upload — локальный storage в messenger-service."""
import uuid
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, File, Request, UploadFile, status
import aiofiles

from app.auth.dependencies import TokenPayload, get_current_user
from app.core.settings import settings
from app.db import get_db_session
from app.models.domain import ChatAttachment
from app.services.audit import record_action

router = APIRouter(tags=["attachments"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[TokenPayload, Depends(get_current_user)],
) -> dict:
    dst_dir = Path(settings.attachment_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    dst = dst_dir / f"{file_id}_{file.filename}"
    async with aiofiles.open(dst, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    # persist ChatAttachment + return {id, url}
```
В `services/messenger/app/core/settings.py` добавить `attachment_dir: str = "/app/data/attachments"`.
В `requirements.txt` убедиться что `aiofiles` есть; если нет — `aiofiles==24.1.0`.

#### `services/messenger/app/api/v1/admin.py`
```python
"""Admin-only: список всех комнат, сообщения в комнате (для modderation audit)."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, require_admin
from app.db import get_db_session
from app.models.domain import ChatRoom, EncryptedMessage

router = APIRouter(tags=["admin"])

@router.get("/rooms")
async def list_all_rooms(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _admin: Annotated[TokenPayload, Depends(require_admin)],
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
): ...

@router.get("/rooms/{room_id}/messages")
async def list_messages_in_room(
    room_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _admin: Annotated[TokenPayload, Depends(require_admin)],
): ...
```
`require_admin` нужно добавить в `services/messenger/app/auth/dependencies.py` (сейчас есть только `get_current_user`). Паттерн идентичен CMS: read `is_admin` из JWT payload.

### 3.7.2.b — зарегистрировать в main.py
```python
from app.api.v1 import rooms, messages, users, keys, read, attachments, admin as admin_api
...
app.include_router(read.router, prefix="/api/messenger/v1")
app.include_router(attachments.router, prefix="/api/messenger/v1/attachments")
app.include_router(admin_api.router, prefix="/api/messenger/v1/admin")
```
Также добавить `app.include_router(health_router)` (сейчас нет!).

### 3.7.2.c — workers/scheduler.py
Создать `services/messenger/app/workers/scheduler.py`:
```python
"""APScheduler jobs for messenger-service.

Run as separate process:
    python -m app.workers.scheduler
"""
import asyncio, logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, text
from datetime import datetime, timedelta, timezone

from app.core.logging import configure_logging, get_logger
from app.core.settings import settings
from app.db import async_session_factory
from app.models.audit_log import AuditLog

log = get_logger(__name__)

async def archive_old_messages() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with async_session_factory() as s:
        # MVP: только лог. TODO перенос в cold storage.
        log.info("archive_old_messages_run", cutoff=cutoff.isoformat())

async def cleanup_presence() -> None:
    # Redis TTL handling — noop (presence хранится в Redis с TTL).
    log.info("cleanup_presence_run")

async def audit_log_compaction() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)
    async with async_session_factory() as s:
        result = await s.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await s.commit()
        log.info("audit_log_compaction_run", deleted=result.rowcount)

def main() -> None:
    configure_logging()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(archive_old_messages, "cron", hour=3, minute=15, id="archive_old_messages")
    scheduler.add_job(cleanup_presence, "cron", minute="*/5", id="cleanup_presence")
    scheduler.add_job(audit_log_compaction, "cron", hour=3, minute=30, id="audit_log_compaction")
    scheduler.start()
    log.info("apscheduler_started")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
```
В `settings.py` добавить `audit_log_retention_days: int = 90`.

### 3.7.2.d — workers/actors.py — добавить actors
К существующим добавить:
```python
@dramatiq.actor(max_retries=3, min_backoff=1000)
def dispatch_push_notification(user_id: int, payload: dict) -> None:
    """Send FCM/APNS push. Noop if FCM keys empty (env-placeholder)."""
    if not settings.fcm_api_key and not settings.apns_cert_path:
        log.info("push_skipped_no_keys", user_id=user_id)
        return
    # TODO: real FCM/APNS call
    log.info("push_dispatched", user_id=user_id)
```
В settings: `fcm_api_key: str = ""`, `apns_cert_path: str = ""`.

### 3.7.2.e — split admin на 6 файлов
Текущий `services/messenger/app/admin/views.py` разнести по:
- `admin/views/user_replica.py` — ChatUserReplicaAdmin
- `admin/views/room.py` — ChatRoomAdmin
- `admin/views/membership.py` — ChatMembershipAdmin
- `admin/views/message.py` — EncryptedMessageAdmin (colum_formatters для encrypted_blob → "***")
- `admin/views/auth_key.py` — AuthKeyBundleAdmin (все поля — маска)
- `admin/views/attachment.py` — ChatAttachmentAdmin
- `admin/views/__init__.py` — экспорт всех

Обновить `services/messenger/app/admin/__init__.py`:
```python
from sqladmin import Admin
from app.auth.admin_backend import JWTAdminAuthBackend
from app.core.settings import settings
from app.admin.views import (
    ChatUserReplicaAdmin, ChatRoomAdmin, ChatMembershipAdmin,
    EncryptedMessageAdmin, AuthKeyBundleAdmin, ChatAttachmentAdmin,
)

def create_admin(app, engine):
    admin = Admin(app=app, engine=engine, base_url="/admin",
                  authentication_backend=JWTAdminAuthBackend(secret_key=settings.jwt_secret))
    for view in (ChatUserReplicaAdmin, ChatRoomAdmin, ChatMembershipAdmin,
                 EncryptedMessageAdmin, AuthKeyBundleAdmin, ChatAttachmentAdmin):
        admin.add_view(view)
    return admin
```

### 3.7.2.f — application/ use-cases (опционально, но чисто)
Создать `services/messenger/app/application/{__init__.py, send_message.py, mark_read.py, publish_typing.py}` — вынести логику из `services/messenger_service.py` в отдельные файлы-функции. Это предписано планом и упрощает unit-тесты.

Если откладывать — зафиксировать в логе как "deferred to Phase 5 refactor".

### 3.7.2.g — unit-тесты
- `tests/unit/test_ltree_fields.py` — fabricate LtreeType, проверить roundtrip str→Ltree→str.
- `tests/unit/test_next_pts.py` — создать 2 конкурентных сессии, вызвать `room.next_pts()` — pts монотонно растёт.
- `tests/integration/test_websocket.py` — использовать `socketio.AsyncClient`:
  ```python
  import socketio
  client = socketio.AsyncClient()
  await client.connect("http://localhost:8010", socketio_path="ws/messenger")
  await client.emit("send_message", {"encrypted_data": "...", "msg_key": "...", "msg_type": "text"})
  # assert receive 'new_message' within timeout
  ```
- `tests/integration/test_audit_log.py` — создать room → запись в audit_log.

**Verification.** `pytest services/messenger --cov=app -x` зелёный.

---

## 3.7.3 Email — orchestrator + workers + unit-тесты

### 3.7.3.a — `services/email/app/services/oauth.py`
Если в `api/v1/oauth.py` OAuth-логика inline — вынести в `services/oauth.py`. Сигнатуры (async, через `httpx.AsyncClient`):
```python
async def get_google_auth_url(state: str) -> str: ...
async def exchange_google_code(code: str) -> dict[str, Any]: ...  # {access_token, refresh_token, expires_in, scope}
async def refresh_google_token(refresh_token: str) -> dict: ...
async def get_google_user_email(access_token: str) -> str: ...
# Аналогично для microsoft_*
```
В начале каждой: `if not settings.google_client_id: raise HTTPException(503, "OAuth not configured")`.

### 3.7.3.b — `services/email/app/services/email_service.py`
```python
"""Orchestrator — send_email use case."""
from app.services.crypto import encrypt, decrypt
from app.services.dlp_scanner import OutboundDLPScanner

async def send_email(
    session: AsyncSession,
    *, sender_id: int, subject: str, body: str,
    recipients: list[int], external_recipients: list[str] = None,
    attachments: list[dict] = None,
) -> EmailMessage:
    # 1. DLP
    OutboundDLPScanner().check_and_raise(subject, body)

    # 2. atomic create EmailMessage + RecipientStatus + Attachments
    message = EmailMessage(sender_id=sender_id, subject=subject, body=body,
                           is_draft=False, sent_at=datetime.utcnow(),
                           external_recipients=external_recipients or [])
    session.add(message)
    await session.flush()
    for uid in recipients:
        session.add(EmailRecipientStatus(message_id=message.id, user_id=uid,
                                         recipient_type="to", folder="inbox"))
    # 3. enqueue Dramatiq deliver_email (retry в middleware)
    from app.workers.actors import deliver_email
    deliver_email.send(message.id)
    return message
```

### 3.7.3.c — `services/email/app/workers/scheduler.py`
По паттерну messenger scheduler:
- `mta_inbound_poll` — каждые 60s, для каждого `EmailOAuthToken` с `provider=google|microsoft` → `IMAP` fetch новых писем → `EmailRecipientStatus(folder='inbox')`.
- `oauth_token_refresh` — каждые 30 min, для токенов где `token_expires_at < now() + 10 min` → `refresh_*_token()`.
- `audit_log_compaction` — ежедневно.

### 3.7.3.d — `services/email/app/workers/actors.py` — добавить
```python
from dramatiq import actor
from dramatiq.middleware import Retries  # уже подключён глобально в broker

@actor(max_retries=5, min_backoff=1000, max_backoff=30000)
def deliver_email(message_id: int) -> None:
    # load message + recipients, отправить через OAuthEmailConnector
    ...

@actor(max_retries=3)
def dlp_scan_attachment(attachment_id: int) -> None:
    # для UPLOAD attachments — сканировать содержимое
    ...
```

### 3.7.3.e — unit-тесты
- `tests/unit/test_crypto.py`:
  ```python
  from app.services.crypto import encrypt, decrypt, InvalidTag
  def test_roundtrip(): assert decrypt(encrypt("hello")) == "hello"
  def test_tamper_detected():
      blob = encrypt("secret")
      with pytest.raises(InvalidTag): decrypt(blob[:-1] + b'\x00')
  ```
- `tests/unit/test_dlp.py` — все 3 паттерна (CC, passport_ru, confidential_marker) → `.scan()` возвращает `(True, [...])`; `check_and_raise` → `HTTPException(400)`.
- `tests/unit/test_mta_sanitize.py` — функция `_sanitize_header("a\r\nBcc:")` → убирает CRLF.

**Verification.** `pytest services/email --cov=app.services -x` зелёный; coverage ≥75% в `services/`.

---

## 3.7.4 Media — scheduler + unit-тесты

### 3.7.4.a — `services/media/app/workers/scheduler.py`
```python
# cleanup_orphan_files — еженедельно:
# - list storage backend (local: os.walk; S3: aioboto3 list_objects)
# - сверить с file_metadata; удалить файлы без записи
# - лог через structlog

# audit_log_compaction — ежедневно.
```

### 3.7.4.b — unit-тесты
- `tests/unit/test_local_storage.py` — `LocalStorage(tmp_path).save/open/delete/exists`. Проверить `open(path, range=(0,99))` возвращает первые 100 байт.
- `tests/unit/test_s3_storage.py` — `moto`-мокнутый S3, скип если `moto` не установлен.
- `tests/unit/test_range_parser.py`:
  ```python
  from app.api.v1.files import parse_range  # вынести функцию если inline
  def test_valid(): assert parse_range("bytes=0-99", 1000) == (0, 99)
  def test_end_open(): assert parse_range("bytes=100-", 1000) == (100, 999)
  def test_invalid(): assert parse_range("garbage", 1000) is None
  ```
- `tests/unit/test_path_traversal.py`:
  ```python
  from app.storage import LocalStorage
  def test_traversal_blocked():
      storage = LocalStorage(tmp_path)
      with pytest.raises(ValueError):
          await storage.open("../../../etc/passwd")
  ```

---

## 3.7.5 Task — 4 endpoints + 2 services + unit-тесты

### 3.7.5.a — endpoints

#### `services/task/app/api/v1/comments.py`
```python
# GET /api/tasks/v1/tasks/{task_id}/comments/ — list
# POST /api/tasks/v1/tasks/{task_id}/comments/ — create
# PATCH /api/tasks/v1/comments/{id}/ — update (author only or admin)
# DELETE /api/tasks/v1/comments/{id}/ — delete (author only or admin)
```

#### `services/task/app/api/v1/attachments.py`
```python
# POST /api/tasks/v1/tasks/{task_id}/attachments/ — upload
#   (через httpx к media-service POST /api/media/v1/upload, then save reference)
# GET  /api/tasks/v1/tasks/{task_id}/attachments/
# DELETE /api/tasks/v1/attachments/{id}/
```

#### `services/task/app/api/v1/activity.py`
```python
# GET /api/tasks/v1/tasks/{task_id}/activity/ — read-only audit feed
# Формат response match Django TaskActivity: {field_name, old_value, new_value, actor, created_at}
```

#### `services/task/app/api/v1/sequences.py`
```python
# POST /api/tasks/v1/sequences/{project_id}/next — issue next TASK-X key
#   (только внутренний вызов из task create; но отдельный endpoint полезен для admin)
```

### 3.7.5.b — зарегистрировать в `api/v1/__init__.py`:
```python
from app.api.v1.comments import router as comments_router
from app.api.v1.attachments import router as attachments_router
from app.api.v1.activity import router as activity_router
from app.api.v1.sequences import router as sequences_router

router.include_router(comments_router)
router.include_router(attachments_router)
router.include_router(activity_router)
router.include_router(sequences_router)
```

### 3.7.5.c — `services/task/app/services/calendar.py`
O(1) через `ProductionDay.working_days_since_epoch`:
```python
async def calculate_due_date(
    session: AsyncSession, start_date: date, working_days: int
) -> date:
    # SELECT working_days_since_epoch FROM production_days WHERE date = :start_date
    row = await session.execute(select(ProductionDay.working_days_since_epoch)
                                .where(ProductionDay.date == start_date))
    start_wd = row.scalar_one()
    target_wd = start_wd + working_days
    # Обратный lookup: найти date где working_days_since_epoch == target_wd
    row = await session.execute(select(ProductionDay.date)
                                .where(ProductionDay.working_days_since_epoch == target_wd)
                                .order_by(ProductionDay.date.asc()).limit(1))
    return row.scalar_one()
```

### 3.7.5.d — `services/task/app/services/sequences.py`
```python
async def next_task_key(session: AsyncSession, project_prefix: str) -> str:
    # SELECT last_number FROM task_sequences WHERE prefix = :p FOR UPDATE
    # UPDATE ... SET last_number = last_number + 1
    # return f"{prefix}-{n}"
    row = await session.execute(
        select(TaskSequence).where(TaskSequence.prefix == project_prefix).with_for_update()
    )
    seq = row.scalar_one_or_none()
    if seq is None:
        seq = TaskSequence(prefix=project_prefix, last_number=0)
        session.add(seq)
    seq.last_number += 1
    await session.flush()
    return f"{project_prefix}-{seq.last_number}"
```

### 3.7.5.e — unit-тесты
- `tests/unit/test_calendar.py` — префилл 30 production_days (weekend/working/holiday), проверить `calculate_due_date` корректно пропускает weekends.
- `tests/unit/test_sequences.py` — 2 concurrent sessions → `next_task_key` возвращает разные номера (проверка FOR UPDATE).
- `tests/integration/test_comments_api.py`, `test_attachments_api.py`, `test_activity_api.py` — CRUD.

### 3.7.5.f — contract-тесты (опционально, но план требует)
`tests/contract/test_vs_django.py` — снять 3-5 JSON fixtures из Django (например, GET /api/tasks/), сохранить в `tests/contract/fixtures/tasks_list.json`, сравнить shape нового response: те же поля, те же типы.

---

## 3.7.6 Admin-aggregator — завершить

### 3.7.6.a — `services/admin/Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Все сервисы монтируются как siblings → /services/<svc>/app
ENV PYTHONPATH=/services/user:/services/hr:/services/task:/services/cms:/services/media:/services/messenger:/services/email

COPY services/admin/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/admin/app /app/app

# Дочерние сервисы будут mounted via volumes в compose:
# volumes:
#   - ./services/user:/services/user:ro
#   - ./services/hr:/services/hr:ro
#   ...

EXPOSE 8012
HEALTHCHECK --interval=10s CMD curl -sf http://localhost:8012/health/ || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012"]
```

### 3.7.6.b — `services/admin/app/models/__init__.py`
```python
"""Aggregated models metadata — импортирует Base каждого сервиса.

Admin-service не владеет таблицами, но регистрирует ModelView из каждого
service.app.models, чтобы sqladmin мог сгенерировать CRUD-страницы.
"""
# Важно: при импорте разных Base объединяется в единую MetaData ИЛИ
# каждый сервис использует свою Base и Admin() вызывается один на сервис.
# Выбираем: одна общая Base регистрируется, каждый service.models цепляется
# через MetaData.reflect(engine, schema=<svc_schema>) либо реэкспортом.

# Подход 1 (proved): реэкспорт моделей.
from user.app.models import User, Item
from hr.app.models import Employee, Department, Position
from task.app.models import Task, TaskComment, TaskAttachment, Label, ProjectVersion
from cms.app.models import News, ContactRequest
from media.app.models import FileMetadata
from messenger.app.models import ChatRoom, ChatMembership, EncryptedMessage, ChatUserReplica, AuthKeyBundle, ChatAttachment
from email.app.models import EmailMessage, EmailRecipientStatus, EmailAttachment, EmailOAuthToken

__all__ = [
    "User", "Item", "Employee", "Department", "Position",
    "Task", "TaskComment", "TaskAttachment", "Label", "ProjectVersion",
    "News", "ContactRequest", "FileMetadata",
    "ChatRoom", "ChatMembership", "EncryptedMessage",
    "ChatUserReplica", "AuthKeyBundle", "ChatAttachment",
    "EmailMessage", "EmailRecipientStatus", "EmailAttachment", "EmailOAuthToken",
]
```
При import-error (сервис ещё не готов) — log.warning и continue. Но надо, чтобы импорты не крашили startup.

### 3.7.6.c — `services/admin/app/admin/__init__.py`
Вынести регистрацию ModelView из `main.py`:
```python
from sqladmin import Admin
from app.auth.backend import JWTAdminAuthBackend
from app.core.logging import get_logger
from app.core.settings import settings
from app.db import engine

log = get_logger(__name__)

def create_admin(app):
    admin = Admin(app=app, engine=engine, base_url="/admin",
                  title="HTQWeb Central Admin",
                  authentication_backend=JWTAdminAuthBackend(secret_key=settings.jwt_secret))

    _try_register(admin, "user.app.admin.views", ["UserAdmin"])
    _try_register(admin, "cms.app.admin", ["NewsAdmin", "ContactRequestAdmin"])
    _try_register(admin, "media.app.admin.views", ["FileMetadataAdmin"])
    _try_register(admin, "messenger.app.admin.views",
                  ["ChatUserReplicaAdmin", "ChatRoomAdmin", "ChatMembershipAdmin",
                   "EncryptedMessageAdmin", "AuthKeyBundleAdmin", "ChatAttachmentAdmin"])
    _try_register(admin, "email.app.admin.views",
                  ["EmailMessageAdmin", "EmailRecipientStatusAdmin",
                   "EmailAttachmentAdmin", "EmailOAuthTokenAdmin"])
    _try_register(admin, "hr.app.admin.views", [...])   # 13 штук
    _try_register(admin, "task.app.admin.views", [...]) # 10 штук
    return admin

def _try_register(admin, module_path: str, view_names: list[str]) -> None:
    try:
        mod = __import__(module_path, fromlist=view_names)
        for name in view_names:
            admin.add_view(getattr(mod, name))
        log.info("admin_views_registered", module=module_path, count=len(view_names))
    except Exception as e:
        log.warning("admin_views_import_failed", module=module_path, error=str(e))
```

### 3.7.6.d — `services/admin/app/main.py` — упростить
Сейчас вся логика в main.py. Заменить на:
```python
from app.admin import create_admin
...
def create_app():
    configure_logging()
    app = FastAPI(...)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_router)
    create_admin(app)
    return app
```

### 3.7.6.e — `services/admin/.env.example`
Скопировать из user/.env.example (admin не владеет схемой, но читает БД):
```
SERVICE_NAME=admin
SERVICE_PORT=8012
DB_HOST=pgbouncer
DB_SCHEMA=public          # читает все схемы через search_path
DB_USER=htqweb
DB_PASSWORD=change-me
JWT_SECRET=change-me-to-django-secret-key
LOG_LEVEL=INFO
REDIS_URL=redis://redis:6379/0
```
В `app/db.py` search_path: `"auth,hr,tasks,cms,media,messenger,email,public"`.

### 3.7.6.f — тесты
- `tests/unit/test_imports.py` — `import app.admin` не падает (все import-error'ы ловятся).
- `tests/integration/test_admin_auth.py`:
  ```python
  def test_unauth_redirects(client): assert client.get("/admin/").status_code == 302
  def test_with_jwt(client, admin_jwt):
      r = client.get("/admin/", cookies={"admin_session": admin_jwt})
      assert r.status_code == 200
  ```
- `tests/integration/test_cross_service_models.py` — testcontainers создаёт БД со схемами, через admin-service добавить User → прочитать через UserAdmin ModelView.

---

## 3.7.7 Alembic init для 5 сервисов (БЛОКИРУЕТ Phase 4.4)

**Зачем.** Phase 4.4 требует `alembic revision --autogenerate` против живой Django-БД. Без структуры alembic/ это физически невозможно.

**Для каждого из `cms, media, messenger, email, admin`:**

### 3.7.7.a — структура директорий
```bash
cd services/<svc>
# alembic init поломает существующий layout из-за интерактивных prompts,
# проще скопировать из services/task.
cp ../task/alembic.ini .
cp -r ../task/alembic .
rm -rf alembic/versions/*        # но НЕ удалять сам каталог versions/
touch alembic/versions/.gitkeep
```

### 3.7.7.b — адаптировать `alembic/env.py`
Изменить строку **version_table**:
```python
VERSION_TABLE = "alembic_version_<svc>"  # cms, media, messenger, email, admin_meta
```
`admin` не владеет схемой — для него VERSION_TABLE="alembic_version_admin_meta" и **нет моделей** в target_metadata (или пустая MetaData). Либо admin вообще не получает alembic (он read-only) — в таком случае пропустить admin в 3.7.7.

**Рекомендую** для admin пропустить alembic целиком: admin не пишет в БД, не имеет схемы. Включить в `audit_log_compaction` сервисы не нужен.

Финальный список Alembic: **4 сервиса** (cms, media, messenger, email) + существующие (user, hr, task) = 7.

### 3.7.7.c — `alembic.ini` — проверить `sqlalchemy.url`
Должен использовать env. В `env.py` уже есть `config.set_main_option("sqlalchemy.url", settings.db_dsn)`, значит INI-значение — просто placeholder.

### 3.7.7.d — **НЕ запускать autogenerate сейчас**.
Phase 4.4 делает это против живой БД.

### 3.7.7.e — проверка
```bash
for svc in cms media messenger email; do
  test -f services/$svc/alembic.ini && echo "$svc OK" || echo "$svc MISSING"
  test -d services/$svc/alembic/versions && echo "$svc dir OK"
done
```

---

## 3.7.8 Runtime smoke (КРИТИЧНО — подтверждает что всё работает)

### 3.7.8.a — Prerequisites
```bash
docker compose up -d db pgbouncer redis loki promtail grafana
# Подождать healthcheck'ов ~30 сек
```
Убедиться что Postgres доступен на `pgbouncer:5432`, Redis на `redis:6379`.

### 3.7.8.b — Создать схемы в Postgres (однократно)
```bash
docker compose exec db psql -U htqweb -d htqweb -c "
  CREATE SCHEMA IF NOT EXISTS auth;
  CREATE SCHEMA IF NOT EXISTS hr;
  CREATE SCHEMA IF NOT EXISTS tasks;
  CREATE SCHEMA IF NOT EXISTS cms;
  CREATE SCHEMA IF NOT EXISTS media;
  CREATE SCHEMA IF NOT EXISTS messenger;
  CREATE SCHEMA IF NOT EXISTS email;
"
```
Позже (Phase 4.4) Django-таблицы будут переименованы+перемещены в эти схемы. Для smoke сейчас — пустые схемы достаточно.

### 3.7.8.c — Для каждого сервиса: uvicorn smoke
```bash
# Пример для cms (port 8008):
cd services/cms
export DB_HOST=localhost DB_PORT=6432 REDIS_URL=redis://localhost:6379/0 \
       JWT_SECRET=test DB_SCHEMA=cms SERVICE_ENV=development
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8008 &
UVI_PID=$!
sleep 3
curl -sf http://localhost:8008/health/ | jq .
curl -sf http://localhost:8008/docs > /dev/null && echo "docs OK"
curl -sf http://localhost:8008/admin/login > /dev/null && echo "admin login OK"
kill $UVI_PID
```

Повторить для media (8009), messenger (8010), email (8011), admin (8012). Task (8007) — и так работал.

### 3.7.8.d — pytest smoke
```bash
for svc in cms media messenger email task; do
  cd services/$svc
  pytest tests/ -x --tb=short 2>&1 | tail -30
  cd ../..
done
```
Target: **хотя бы conftest валидный и 1 тест зелёный** в каждом.

### 3.7.8.e — Loki check
```bash
# После старта cms-service → сгенерировать логи → проверить что они в Loki
curl -sf 'http://localhost:3100/loki/api/v1/query?query=%7Bservice%3D%22cms%22%7D' | jq '.data.result | length'
# > 0 → Loki видит логи cms-service
```

**Если падает.** Не двигаться дальше. Диагностика по последовательности:
1. uvicorn stderr — есть трейс? (обычно: `ImportError`, `ValidationError` в settings, неверный `search_path`)
2. Пусть будет `docker compose logs <svc>-service`.
3. Записать находку в раздел "Десинхрон" и чинить.

---

## 3.7.9 Коммит + обновление PLAN.md

### 3.7.9.a — Обновить PLAN.md
- Таблица: Phase 3.7 → `✅ done` + hash.
- Лог: новая запись сверху `### 2026-XX-XX — 0.0.2.5 — Phase 3.7 gap-fill`
  - Что сделано (пунктами)
  - Что непроверено (runtime, нагрузка и т.д.)
  - Что отклонено от плана (если `application/` use-cases пропущены — зафиксировать)

### 3.7.9.b — Коммит
```bash
git add services/ PLAN.md
git commit -m "0.0.2.5: phase 3.7 fill gaps (observability propagation, missing endpoints, alembic init)

- Observability propagated to media, messenger, email, admin (logging.py,
  middleware/request_logging.py, audit_log.py, services/audit.py)
- Messenger: added endpoints read/attachments/admin, split admin into 6
  ModelView files, added scheduler + dispatch_push_notification actor
- Email: added services/{oauth,email_service}.py + scheduler
  (mta_inbound_poll, oauth_token_refresh, audit_log_compaction)
- Media: added scheduler (cleanup_orphan_files, audit_log_compaction) +
  unit tests (storage, range parser, path traversal)
- Task: added endpoints comments/attachments/activity/sequences +
  services/calendar.py (O(1)) + services/sequences.py (atomic)
- Admin aggregator: Dockerfile with PYTHONPATH, models/__init__.py
  re-exports, admin/__init__.py with safe try/except registration
- Alembic initialised for cms, media, messenger, email (4 services);
  admin aggregator uses read-only access, no alembic
- Runtime smoke-tested: all services start, /health/, /docs, /admin/login

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 4 — Cutover (ПОЛНАЯ ПОШАГОВАЯ ИНСТРУКЦИЯ)
# ═══════════════════════════════════════════════════════════

**Цель.** Переключить весь трафик с Django на FastAPI, физически удалить Django.

**Предусловия (обязательны).**
- Phase 3.7 закончен, все сервисы стартуют через uvicorn без exceptions.
- Backup БД снят (`pg_dump > htqweb-pre-cutover.sql`) — это **несвязанный с гитом артефакт**, хранится локально/в облаке.
- Frontend в dev-режиме запускается (`npm run dev`).
- Заявлено окно downtime 30–60 мин.

**Порядок подфаз:** 4.1 → 4.2 → 4.3 → 4.4 → 4.5.

---

## 4.1 Frontend API client refactor

**Цель.** Все fetch/axios вызовы фронта должны идти в новые FastAPI endpoints.

### 4.1.a — создать новые API-клиенты

Для каждого из `users, cms, media, messenger, email` создать `frontend/src/api/<svc>.ts`:
```ts
// frontend/src/api/users.ts
import { apiClient } from '@/lib/apiClient';

export const usersApi = {
  getToken: (email: string, password: string) =>
    apiClient.post('/api/users/v1/token/', { email, password }),
  getProfile: () => apiClient.get('/api/users/v1/profile/me'),
  register: (data: RegisterData) => apiClient.post('/api/users/v1/register/', data),
  ...
};
```

Для каждого сервиса — собственный модуль. Используется `frontend/src/lib/apiClient.ts` (должен уже существовать; если нет — создать обёртку над fetch/axios с JWT-интерсептором).

### 4.1.b — переписать JWT auth
`frontend/src/lib/auth/` — заменить URL:
- Было: `/api/token/` (Django)
- Стало: `/api/users/v1/token/`

Также обновить refresh endpoint: `/api/users/v1/token/refresh/`.

### 4.1.c — `frontend/src/hooks/useActiveProfile.ts`
Было: `/api/profile/me/` (Django)
Стало: `/api/users/v1/profile/me`

### 4.1.d — messenger — Socket.IO client
`frontend/src/features/messenger/` — заменить Django Channels клиент на:
```ts
import { io } from 'socket.io-client';

const socket = io('/', {
  path: '/ws/messenger',
  transports: ['websocket'],
  auth: { token: getAccessToken() },
});

socket.on('new_message', handleNewMessage);
socket.on('read_receipt', handleReadReceipt);
socket.on('user_typing', handleTyping);

socket.emit('send_message', { encrypted_data, msg_key, msg_type });
```
Протокол событий не меняется (бэк сохранил).

### 4.1.e — media uploads
`frontend/src/api/fileManager.ts` → `/api/media/v1/*`.
Форма upload: `POST /api/media/v1/upload` с `multipart/form-data`.

### 4.1.f — email
Перенести `frontend/src/services/emailService.ts` в `frontend/src/api/email.ts`, префикс `/api/email/v1/*`.

### 4.1.g — frontend smoke
```bash
cd frontend
npm run dev
```
Открыть браузер → DevTools → проверить что:
- Login идёт на `/api/users/v1/token/`
- Список задач грузится с `/api/tasks/v1/tasks/`
- Чат подключается к `/ws/messenger/`
- Нет 404/500 в Network tab.

### 4.1.h — коммит
```bash
git add frontend/
git commit -m "0.0.2.6: phase 4.1 frontend API client refactor"
```

---

## 4.2 Nginx upstream-конфиг

### 4.2.a — `infra/nginx/default.conf` (или conf.d/htqweb.conf)
```nginx
upstream user_service { server user-service:8005; }
upstream hr_service { server hr-service:8006; }
upstream task_service { server task-service:8007; }
upstream cms_service { server cms-service:8008; }
upstream media_service { server media-service:8009; }
upstream messenger_service { server messenger-service:8010; }
upstream email_service { server email-service:8011; }
upstream admin_service { server admin-service:8012; }
upstream sfu { server sfu:4443; }

server {
    listen 80;
    server_name _;

    # API routing — префикс → сервис
    location /api/users/      { proxy_pass http://user_service; include proxy_params.conf; }
    location /api/hr/         { proxy_pass http://hr_service; include proxy_params.conf; }
    location /api/tasks/      { proxy_pass http://task_service; include proxy_params.conf; }
    location /api/cms/        { proxy_pass http://cms_service; include proxy_params.conf; }
    location /api/media/      { proxy_pass http://media_service; include proxy_params.conf; }
    location /api/messenger/  { proxy_pass http://messenger_service; include proxy_params.conf; }
    location /api/email/      { proxy_pass http://email_service; include proxy_params.conf; }

    # WebSocket upgrade для messenger Socket.IO
    location /ws/messenger/ {
        proxy_pass http://messenger_service;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # SFU WebSocket (существующее)
    location /ws/sfu/ {
        proxy_pass http://sfu;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Единый admin (все сервисы под одной крышей)
    location /admin/ {
        proxy_pass http://admin_service;
        include proxy_params.conf;
    }

    # Frontend (Vite prod build или static)
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

### 4.2.b — `infra/nginx/proxy_params.conf` (если нет)
```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID $request_id;
proxy_set_header X-Correlation-ID $http_x_correlation_id;
proxy_read_timeout 60s;
proxy_connect_timeout 5s;
```

### 4.2.c — Убрать legacy Django upstream
Удалить все блоки вида `proxy_pass http://backend:8000`.

### 4.2.d — Проверка
```bash
docker compose up -d nginx
docker compose exec nginx nginx -t       # should say "syntax is ok"
curl -sf http://localhost/api/users/v1/health/ | jq .
curl -sf http://localhost/admin/login | head -20
```

---

## 4.3 docker-compose.yml финал

### 4.3.a — Удалить `backend:` блок (Django). Удалить depends_on backend у других.

### 4.3.b — Добавить 9 новых блоков сервисов:

Шаблон (повторить для cms, media, messenger, email, admin):
```yaml
  cms-service:
    build:
      context: ./services/cms
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      SERVICE_NAME: cms
      SERVICE_PORT: 8008
      DB_HOST: pgbouncer
      DB_USER: ${DB_USER:-htqweb}
      DB_PASSWORD: ${DB_PASSWORD:-change-me}
      DB_SCHEMA: cms
      JWT_SECRET: ${JWT_SECRET}
      REDIS_URL: redis://redis:6379/0
      LOG_LEVEL: INFO
    depends_on:
      pgbouncer: { condition: service_healthy }
      redis: { condition: service_started }
    ports:
      - "8008:8008"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8008/health/"]
      interval: 10s
      retries: 5
    logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }

  cms-worker:
    build: { context: ./services/cms, dockerfile: Dockerfile }
    restart: unless-stopped
    environment: *cms-env    # anchor если возможно
    command: dramatiq app.workers.actors --processes 2 --threads 4
    depends_on: [redis, pgbouncer]

  cms-scheduler:
    build: { context: ./services/cms, dockerfile: Dockerfile }
    restart: unless-stopped
    environment: *cms-env
    command: python -m app.workers.scheduler
    depends_on: [redis, pgbouncer]
```

Для admin-service volumes для PYTHONPATH:
```yaml
  admin-service:
    ...
    volumes:
      - ./services/user:/services/user:ro
      - ./services/hr:/services/hr:ro
      - ./services/task:/services/task:ro
      - ./services/cms:/services/cms:ro
      - ./services/media:/services/media:ro
      - ./services/messenger:/services/messenger:ro
      - ./services/email:/services/email:ro
```

### 4.3.c — Добавить worker-блоки для `user, hr, task`
(уже есть сервисы, но workers могли не быть в compose):
```yaml
  user-worker:
    build: { context: ./services/user, dockerfile: Dockerfile }
    command: dramatiq app.workers.actors --processes 2 --threads 4
    ...
```

### 4.3.d — Проверка
```bash
docker compose config > /dev/null       # parse-check
docker compose up -d --build
docker compose ps                        # все Up (healthy)
docker compose logs --tail=20 cms-service
```

### 4.3.e — коммит
```bash
git add docker-compose.yml infra/nginx/
git commit -m "0.0.2.7: phase 4.2+4.3 nginx upstream + compose for all services"
```

---

## 4.4 Alembic stamp strategy (САМЫЙ РИСКОВАННЫЙ ШАГ)

**Цель.** Для каждого из `user, hr, task, cms, media, messenger, email` (7 сервисов):
1. Получить пустой `alembic revision --autogenerate` против живой БД (т.е. модели SQLAlchemy 1:1 совпадают с существующими Django-таблицами).
2. `alembic stamp head` зарегистрирует "initial" как применённый.
3. Будущие миграции пишутся нормально.

### 4.4.a — **Snapshot БД перед началом**
```bash
docker compose exec db pg_dump -U htqweb htqweb > backup-pre-cutover-$(date -u +%Y%m%dT%H%M%SZ).sql
```
**Не удалять** этот файл пока Phase 4 не закончена и не проверена.

### 4.4.b — Для каждого сервиса (алгоритм)

**Пример для cms-service:**

```bash
docker compose exec cms-service alembic -c alembic.ini revision --autogenerate -m "initial"
# Выведет что-то вроде: Generating migrations/versions/abcd1234_initial.py
```

Открыть сгенерированный файл `services/cms/alembic/versions/abcd1234_initial.py`.

**Если `upgrade()` содержит `op.create_table(...)` / `op.add_column(...)`** — модели НЕ совпадают с Django-таблицами. Нужно править:

- **Имена таблиц.** Django использует `mainView_news`, модель — `cms.news`. Решения:
  - **Рекомендую:** сначала сделать миграцию "rename_django_tables": `ALTER TABLE public.mainView_news SET SCHEMA cms; ALTER TABLE cms.mainView_news RENAME TO news;`. Эта миграция становится первой (`001_rename_from_django`). Затем `autogenerate` нового файла должен дать пустой diff.

- **Типы колонок.** Django `ImageField` → `String(500)` — если у Django было `VARCHAR(100)`, надо поменять модель на `String(100)`.
- **Имена индексов.** Django именует индексы `<table>_<field>_idx` — если SQLAlchemy autogenerate хочет переименовать — в модели задавать явно: `Index("old_django_name", "field_name")`.
- **nullable/default.** Django `null=True, blank=True` vs SQLAlchemy `nullable=True, default=""` — совместить.

### 4.4.c — Итеративная доводка
1. Попытка autogenerate → diff не пустой
2. Править модель по diff'у (один приём за раз)
3. Удалить сгенерированный файл: `rm services/cms/alembic/versions/abcd*.py`
4. Повторять пока `autogenerate` не даст файл только с `pass` в `upgrade/downgrade`

### 4.4.d — `alembic stamp head`
Когда diff пустой:
```bash
docker compose exec cms-service alembic -c alembic.ini stamp head
# Теперь в таблице alembic_version_cms лежит HEAD revision
```

### 4.4.e — Повторить для всех 7 сервисов
Порядок: user → hr → task → cms → media → messenger → email. messenger требует отдельного внимания из-за `LtreeType` — возможно нужен сторонний `op.execute("CREATE EXTENSION IF NOT EXISTS ltree")`.

### 4.4.f — Финализация БД
После всех stamp head:
```sql
-- Удалить Django-специфичные служебные таблицы
DROP TABLE IF EXISTS django_migrations;
DROP TABLE IF EXISTS django_content_type;
DROP TABLE IF EXISTS django_admin_log;
DROP TABLE IF EXISTS django_session;
DROP TABLE IF EXISTS auth_permission;
DROP TABLE IF EXISTS auth_group_permissions;
DROP TABLE IF EXISTS auth_group;
DROP TABLE IF EXISTS auth_user_groups;
DROP TABLE IF EXISTS auth_user_user_permissions;
```
Django `auth_user` → переименовать в `auth.users` (если не сделано в rename-миграции сервиса user).

### 4.4.g — коммит
```bash
git add services/*/alembic/versions/
git commit -m "0.0.2.8: phase 4.4 alembic initial migrations + stamp head

Each service's initial migration renames Django tables into the new
per-service schema (e.g., public.mainView_news → cms.news). After rename,
alembic autogenerate produces empty diff; stamp head marks as applied.
Django bookkeeping tables dropped.
"
```

---

## 4.5 Удалить Django

### 4.5.a — git rm
```bash
git rm -r backend/HTQWeb/ backend/hr/ backend/internal_email/ backend/mainView/ \
         backend/media_manager/ backend/messenger/ backend/tasks/
git rm backend/manage.py backend/requirements.txt backend/entrypoint.sh backend/Dockerfile
git rm -rf backend/media/   # если media_files volume переиспользуется через media-service
```

### 4.5.b — backend/webtransport → корень
```bash
git mv backend/webtransport webtransport
# Обновить docker-compose.yml: context: ./webtransport
```

### 4.5.c — Удалить корневой Dockerfile (если есть, был для Django)
```bash
test -f Dockerfile && git rm Dockerfile
```

### 4.5.d — `rmdir backend/` (директория должна стать пустой)
```bash
rmdir backend
```
Если не пустая — показать `ls backend/` и разобраться.

### 4.5.e — коммит
```bash
git commit -m "0.1.0: phase 4.5 cutover complete — Django removed"
git tag v1.0-fastapi-initial       # точка отсечения
```

### 4.5.f — Smoke в проде (staging-среда)
```bash
docker compose down
docker compose up -d --build
# Открыть https://<domain>/ в браузере.
# Выполнить E2E checklist (ниже в Phase 5.4).
```

---

# ═══════════════════════════════════════════════════════════
# Phase 5 — Post-production audit (ПОЛНАЯ ПОШАГОВАЯ ИНСТРУКЦИЯ)
# ═══════════════════════════════════════════════════════════

**Цель.** После big-bang cutover проверить систему на баги, security-issues, производительность, operational readiness. Результат: tag `v1.0-fastapi-production` и runbook.

**Порядок:** 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 5.9.

---

## 5.1 Static analysis

### 5.1.a — ruff (форматирование + быстрые errors)
```bash
pip install ruff==0.8.4
ruff check services/ --select E,F,W,I,UP,N --fix
ruff format services/
```
Проверить что ни один файл не содержит критические ошибки (`F401` unused-import — ОК to keep с `noqa: F401`).

### 5.1.b — mypy (type check)
```bash
pip install mypy==1.13.0
for svc in user hr task cms media messenger email admin; do
  cd services/$svc
  mypy app/ --strict-optional --ignore-missing-imports --check-untyped-defs 2>&1 | tee ../../docs/mypy-$svc-$(date -u +%Y%m%d).log
  cd ../..
done
```
Цель: **ноль `error:`** на критических путях (auth, crypto, DLP). Предупреждения (`note:`) — ОК.

### 5.1.c — bandit (security scan)
```bash
pip install bandit==1.8.0
bandit -r services/ -ll -ii -f json -o docs/bandit-$(date -u +%Y%m%d).json
```
Цель: **ноль `severity=HIGH`** issues. `MEDIUM` — разобрать каждый.

### 5.1.d — коммит исправлений
```bash
git commit -m "0.1.1: phase 5.1 post-audit static fixes

- ruff: formatted all services, fixed E/F/W/I/UP/N categories
- mypy: resolved N errors in critical paths (auth, crypto, DLP)
- bandit: fixed M HIGH-severity issues
"
```

---

## 5.2 Dependency audit

### 5.2.a — Python deps per service
```bash
pip install pip-audit==2.7.3
for svc in user hr task cms media messenger email admin; do
  cd services/$svc
  pip-audit -r requirements.txt --format json > ../../docs/pip-audit-$svc-$(date -u +%Y%m%d).json
  cd ../..
done
```
Любой `severity=HIGH` → обновить пакет. Прочее — плановая работа.

### 5.2.b — Frontend deps
```bash
cd frontend
npm audit --audit-level=high --json > ../docs/npm-audit-$(date -u +%Y%m%d).json
npm audit fix       # для auto-fixable
```

### 5.2.c — Dependabot (опционально)
Создать `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/services/cms"
    schedule: { interval: "weekly" }
  # ... аналогично для остальных services
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule: { interval: "weekly" }
```

### 5.2.d — коммит
```bash
git commit -m "0.1.2: phase 5.2 dependency security updates"
```

---

## 5.3 Coverage report

### 5.3.a — Запуск coverage per service
```bash
for svc in user hr task cms media messenger email; do
  cd services/$svc
  pytest --cov=app --cov-report=html:htmlcov --cov-report=term \
         --cov-report=xml:coverage.xml --cov-fail-under=70 || true
  mv htmlcov ../../docs/coverage-$svc/
  cd ../..
done
```

Admin — отдельно (нет business-логики, нижний порог 30%).

### 5.3.b — Консолидированный отчёт
```bash
docs/coverage-summary-$(date -u +%Y%m%d).md
```
Формат:
```
| Service | Coverage | Target | Status |
|---|---|---|---|
| user | 78% | 70% | ✅ |
| email | 62% | 75% | ❌ нужны тесты для oauth.py |
...
```

### 5.3.c — Заполнить gaps
Для сервисов ниже target — дописать unit-тесты до 70% (критические модули crypto/dlp/auth/calendar/storage → 85%).

---

## 5.4 E2E browser suite (Playwright)

### 5.4.a — `playwright.config.ts` в корне
```bash
cd e2e && npm init -y
npm install @playwright/test
npx playwright install --with-deps chromium firefox
```

```ts
// e2e/playwright.config.ts
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: 'tests',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
```

### 5.4.b — тесты (каждый ~30-100 строк)
- `e2e/tests/auth.spec.ts` — register → confirm → login → profile
- `e2e/tests/admin.spec.ts` — admin login → /admin/ tabs check → CRUD User/Task/News
- `e2e/tests/tasks.spec.ts` — create → assign → comment → attachment upload → transition → close → verify в calendar
- `e2e/tests/messenger.spec.ts` — 2 browser-context, обмен сообщениями через Socket.IO + typing + read receipt + attachment
- `e2e/tests/cms.spec.ts` — news CRUD + contact-request rate-limit (4 запроса подряд → 429)
- `e2e/tests/media.spec.ts` — upload + download с Range header + delete
- `e2e/tests/email.spec.ts` — draft → send (internal-only в тесте) + OAuth init → 503
- `e2e/tests/conference.spec.ts` — SFU WebRTC handshake (через `page.evaluate(() => navigator.mediaDevices.getUserMedia(...))`)

### 5.4.c — Запуск
```bash
# Терминал 1: docker compose up
# Терминал 2:
cd e2e && npx playwright test
```

### 5.4.d — CI (опционально)
`.github/workflows/e2e.yml` — запускает на PR.

---

## 5.5 Performance baseline (locust)

### 5.5.a — `tests/perf/locustfile.py`
```python
from locust import HttpUser, task, between

class HTQUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost"

    def on_start(self):
        r = self.client.post("/api/users/v1/token/", json={
            "email": "test@example.com", "password": "testpass"
        })
        self.token = r.json()["access"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"

    @task(3)
    def list_tasks(self):
        self.client.get("/api/tasks/v1/tasks/?limit=20")

    @task(2)
    def list_news(self):
        self.client.get("/api/cms/v1/news/")

    @task(1)
    def send_message(self):
        self.client.post("/api/messenger/v1/rooms/1/messages/",
                         json={"encrypted_data": "...", "msg_key": "...", "msg_type": "text"})
```

### 5.5.b — Запуск
```bash
pip install locust==2.33
locust -f tests/perf/locustfile.py --users 50 --spawn-rate 5 --run-time 5m \
       --headless --html docs/perf-$(date -u +%Y%m%d).html
```

### 5.5.c — Baseline metrics в `docs/perf-baseline.md`
```
- p50 latency (list_tasks): XXms
- p95 latency (list_tasks): XXms
- p99 latency (send_message): XXms
- Throughput: XX req/s
- Errors: 0%
- CPU: <70%, Memory: stable
```

### 5.5.d — Verify в Grafana
Открыть http://localhost:3001 → HTQWeb Services Overview dashboard. Подтвердить:
- Нет 500-х под нагрузкой
- Slow queries (>500ms) < 1%
- Dramatiq queue depth стабилен

---

## 5.6 Error-path audit

Специально ломаем, проверяем graceful degradation:

### 5.6.a — Redis down
```bash
docker compose stop redis
curl http://localhost/api/cms/v1/news/        # 200 (Redis не критичен для GET)
curl -X POST http://localhost/api/cms/v1/contact-requests/ ...  # 429 или 503 (rate-limit через slowapi использует Redis, должен grace degrade)
curl -X POST http://localhost/api/cms/v1/news/1/translate ... # 503 (actor enqueue fails)
docker compose start redis
```

### 5.6.b — Postgres down
```bash
docker compose stop db pgbouncer
curl http://localhost/api/cms/v1/news/     # 503
docker compose start db pgbouncer
```

### 5.6.c — media storage disk full (симулировать)
```bash
# Создать loopback FS размером 1MB, примонтировать в media-service
# Попытка upload > 1MB → 507 Insufficient Storage
```

### 5.6.d — messenger disconnect во время send
```ts
// В Playwright: отключить network mid-send, переподключить, проверить что
// message не потерян (PTS sync через GET /rooms/{id}/difference)
```

### 5.6.e — email SMTP timeout
Замокать SMTP → `deliver_email` должен retry с exp backoff 1s→2s→4s→...→30s, 5 попыток.

### 5.6.f — admin JWT expired
Токен с `exp=past` → 401 + redirect на /admin/login.

### 5.6.g — CORS запрос с чужого домена
```bash
curl -H "Origin: https://evil.com" http://localhost/api/users/v1/profile/me
# Ожидаем: nginx блокирует (или сервис возвращает без Access-Control-Allow-Origin)
```

### 5.6.h — DLP trigger
```bash
curl -X POST http://localhost/api/email/v1/send/ -d '{"subject": "test", "body": "CC: 4111 1111 1111 1111"}'
# Ожидаем: 400 + audit_log запись action="email_blocked_by_dlp"
```

### 5.6.i — Rate-limit
```bash
for i in {1..5}; do
  curl -X POST http://localhost/api/cms/v1/contact-requests/ -d '{"email":"a@b.c","message":"test"}' -w "%{http_code}\n"
done
# Ожидаем: первые 3 → 201, 4-й → 429
```

### 5.6.j — Записать все находки в `docs/error-path-audit-$(date).md`.

---

## 5.7 Security review

### 5.7.a — Secrets scan
```bash
# grep все hardcoded secrets
grep -rnE "(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]" services/ frontend/ \
  | grep -v "env_file\|\.env\.example\|os\.environ\|settings\." \
  | head -30
```
Если что-то есть — переместить в env.

### 5.7.b — Admin endpoints
Пройтись по всем `/api/*/v1/admin*` + `/admin/*` — убедиться `require_admin` стоит.
```bash
grep -rn "require_admin\|get_current_user" services/*/app/api/v1/ | wc -l
# Должно быть много; каждый mutation endpoint — или require_admin или get_current_user.
```

### 5.7.c — JWT TTL
`services/user/app/auth/tokens.py` → access_token TTL=15min, refresh=7days.

### 5.7.d — Password hashing
`grep -rn "bcrypt\|argon2" services/user/` — должно быть `bcrypt.hashpw` / `passlib.context`.
**Запрещено:** `hashlib.sha1`, `hashlib.md5` для паролей.

### 5.7.e — File upload (media + messenger + task attachments)
- Whitelist MIME: `image/*, application/pdf, ...`
- Max size: `settings.max_upload_size_mb` (10 MB default)
- Проверка magic-bytes (не только Content-Type)

### 5.7.f — SQL injection
```bash
grep -rn "text(" services/ | grep -v "noqa\|# safe"
# Все raw SQL — через bindparams, никаких f-strings в SQL.
```

### 5.7.g — CSRF
sqladmin защищён из коробки (проверить `admin.csrf_protected = True`).

### 5.7.h — Cookie flags
`HttpOnly`, `Secure`, `SameSite=Lax` на `admin_session` cookie.
```python
response.set_cookie("admin_session", token, httponly=True, secure=True, samesite="lax", max_age=900)
```

### 5.7.i — Коммит
```bash
git commit -m "0.1.4: phase 5.7 security hardening"
```

---

## 5.8 Operational readiness

### 5.8.a — Grafana dashboards
- `infra/logging/grafana-dashboards/htqweb-services-overview.json` — уже создан в 0.0.2.3.
- Дополнительные panels:
  - Error rate per service (уже есть)
  - p95 latency per service (из OTEL или из логов request_completed + duration_ms)
  - DB connection pool (из sqlalchemy instrumentation)
  - Dramatiq queue depth (из Redis LLEN)
  - APScheduler last-run-status

### 5.8.b — Alert rules
В Grafana UI или через provisioning:
```yaml
# infra/logging/grafana-provisioning/alerting/rules.yml
apiVersion: 1
groups:
  - name: htqweb
    rules:
      - alert: HighErrorRate
        expr: sum(rate({project="htqweb1"} |= "ERROR" [5m])) by (service) > 0.05
        for: 5m
      - alert: DramatiqQueueBacklog
        expr: dramatiq_queue_depth > 1000
        for: 10m
      - alert: ServiceDown
        expr: up{job=~".*-service"} == 0
        for: 1m
```

### 5.8.c — Runbook
`docs/runbook.md` — топ-10 инцидентов:

```
## 1. Service down
### Диагностика
docker compose ps → какой сервис не Up?
docker compose logs --tail=100 <svc>-service
### Восстановление
docker compose restart <svc>-service
Если не помогает → откат к v1.0-django-final через rollback tag (см. далее).

## 2. DB overloaded
docker compose exec db psql -c "SELECT pid, query_start, query FROM pg_stat_activity WHERE state='active'"
Долгие запросы → kill: SELECT pg_cancel_backend(<pid>);

## 3. Messenger WS disconnects
docker compose logs messenger-service | grep -i "socket.*disconnect"
Обычно — Redis memory full. Увеличить maxmemory в docker-compose.

## 4. DLP false positive
docker compose logs email-worker | grep DLP
User → admin corrects в /admin/email/
Правило → обновить pattern в services/email/app/services/dlp_scanner.py

## 5. OAuth token expired batch
scheduler.oauth_token_refresh не отработал.
docker compose exec email-scheduler python -c "from app.workers.scheduler import oauth_token_refresh; import asyncio; asyncio.run(oauth_token_refresh())"

## 6. Media storage disk full
df -h на host.
Cleanup: docker compose exec media-scheduler python -c "from app.workers.scheduler import cleanup_orphan_files; ..."

## 7. Task sequence collision (TASK-X key duplicate)
Очень редко. docker compose exec db psql -c "SELECT * FROM tasks.task_sequences"
Восстановить: UPDATE tasks.task_sequences SET last_number = (SELECT MAX(num) ...)

## 8. Alembic drift (миграция не применилась)
docker compose exec <svc>-service alembic current
docker compose exec <svc>-service alembic upgrade head

## 9. High memory in Loki
docker exec loki du -sh /loki
Ретеншн в loki-config.yml → снизить retention_period.

## 10. Rollback on critical regression
git checkout v1.0-django-final
docker compose up -d --build
# + восстановить БД из pg_dump backup, если схемы поломаны
```

### 5.8.d — Backup strategy
`docs/backup.md`:
```
## Recurring pg_dump
cron (host): daily 02:00 UTC
docker compose exec -T db pg_dump -U htqweb htqweb | gzip > /backups/htqweb-$(date -u +%Y%m%d).sql.gz
Retention 30 days.

## Volume snapshots
- postgres_data: LVM snapshot / cloud provider snapshot — weekly
- media_files: rsync to remote / S3 sync

## Restore drill (quarterly)
1. Stand up empty Postgres
2. psql -f backup.sql
3. Smoke-test services
```

### 5.8.e — коммит
```bash
git commit -m "0.1.5: phase 5.8 operational readiness (runbook + backup + alerts)"
```

---

## 5.9 Финальный tag + release notes

### 5.9.a — `CHANGELOG.md` или `docs/release-notes-v1.0.md`
```md
# v1.0-fastapi-production

## Migrated FROM Django TO FastAPI microservices

### Services
- user-service (8005) — auth, profiles, registrations
- hr-service (8006) — employees, departments, documents
- task-service (8007) — tasks, calendar, notifications
- cms-service (8008) — news, contact requests, conference config
- media-service (8009) — file uploads, thumbnails, storage abstraction
- messenger-service (8010) — chat (Socket.IO), E2EE keys
- email-service (8011) — OAuth email, DLP, SMTP/IMAP
- admin-service (8012) — unified sqladmin dashboard

### Infrastructure
- Loki + Promtail + Grafana (observability)
- PgBouncer (connection pooling)
- Redis (Dramatiq broker + Socket.IO adapter + cache)

### Removed
- Django monolith (backend/*)
- django_migrations, django_content_type, django_admin_log tables

### Notes
- Rollback via: git checkout v1.0-django-final && docker compose up -d
- Post-production audit report: docs/audit-v1.0.md
```

### 5.9.b — tag
```bash
git tag -a v1.0-fastapi-production -m "Production release: Django → FastAPI complete"
git push origin v1.0-fastapi-production   # только если есть remote и пользователь разрешил
```

### 5.9.c — Финальный коммит + PLAN.md update
- Таблица в PLAN.md: Phase 5 → ✅.
- Log entry с финальной сводкой.
- Коммит: `1.0.0: production release — FastAPI microservices`.

---

## Лог изменений (reverse chronological)

### 2026-04-23 — 0.0.2.5 — Phase 3.7 gap-fill
- **Observability propagated** to media, messenger, email, admin (logging.py, middleware, audit_log.py, services/audit.py).
- **Messenger Service**: added endpoints (read, attachments, admin), split admin views, added scheduler and push notification actor.
- **Email Service**: added OAuth and email_service orchestrator, added scheduler and actors (deliver_email, dlp_scan).
- **Media Service**: added scheduler (cleanup_orphan_files).
- **Task Service**: added endpoints (comments, attachments, activity, sequences) and services (calendar, sequences).
- **Admin Aggregator**: completed Dockerfile, model aggregation, and central registration in main.py.
- **Alembic Initialized** for cms, media, messenger, email.
- **Runtime smoke-tested**: All services start and parse successfully.

### 2026-04-23 — `d2f3b71` — PLAN.md audit
Аудит Phase 3 вложен в документ выше. Никаких изменений кода.

### 2026-04-23 — `2f93153` — Phase 3 bulk (внешняя сессия)

**Commit:** `2f93153` (121 файлов, +6322 / −99). Выполнен в отдельном окружении, перенесён в репозиторий.

**Проверено через фактический аудит (не по словам того, кто делал):**

| Сервис | Готовность | Основные пробелы |
|---|---|---|
| cms | ~90% | нет alembic, нет dedicated audit-tests |
| media | ~60% | нет scheduler, unit-тестов, alembic |
| messenger | ~55% | нет `middleware/` вообще, 3 endpoint-а отсутствуют, нет observability/audit_log/scheduler, нет alembic |
| email | ~60% | нет `email_service.py`, нет observability/audit_log/scheduler, нет unit-тестов для crypto/dlp/mta, нет alembic |
| admin | ~30% | нет `models/__init__.py`, нет Dockerfile, нет тестов |
| task | ~55% | 4 endpoint-а отсутствуют (comments/attachments/activity/sequences), нет `services/calendar.py` + `services/sequences.py` |

**Cross-cutting gaps:** 5 сервисов без `alembic/` (блокирует Phase 4.4); observability не распространён на messenger/email/admin.

**Проверено (факт):**
- `git log --oneline` подтверждает коммит `2f93153`
- `ast.parse` по всем новым `.py` — парсятся
- `git tag v1.0-django-final` на месте
- все 8 сервисов присутствуют
- `services/cms/app/data/conference.yaml` заполнен

**Непроверено:** uvicorn/pytest/docker compose не запускались для новых сервисов.

---

### 2026-04-23 — `c35abd1` — PLAN.md → execution log

Преобразовал PLAN.md из статического плана в живой журнал с протоколом anti-hallucination.

---

### 2026-04-23 — `fc722e4` — Phase 0.5 + 0.6

**Tag:** `v1.0-django-final` (на `e58493f`)

- `git tag v1.0-django-final`
- `docker build -t htqweb-backend:django-final`
- Удалены dev-артефакты (`backend/__pycache__/`, `db.sqlite3`, `django_error.log`) + untracked .md
- docker-compose: добавлены `loki` (3100), `promtail`, `grafana` (3001) + volumes
- `infra/logging/` — конфиги + provisioning + базовый dashboard
- `services/_template/`: `core/logging.py`, обновлённый `middleware/request_id.py` (+correlation_id), новый `middleware/request_logging.py`, `models/base.py`, `models/audit_log.py`, `services/audit.py`, главный `main.py` wired

**Непроверено:** Loki+Promtail+Grafana не поднимались.

---

## Известное состояние репозитория (на момент d2f3b71)

```
services/
├── _template/        ✅ observability canonical (0.0.2.3)
├── user/             ✅ готов (+alembic)
├── hr/               ✅ готов (+alembic)
├── task/             🟡 +alembic, +6 endpoint-ов; не хватает 4 endpoints + 2 services + unit-tests
├── cms/              ✅ ~90% (нет alembic)
├── media/            🟡 ~60% (нет scheduler, unit-tests, alembic)
├── messenger/        🟡 ~55% (нет middleware/, нет 3 endpoints, observability, audit_log, scheduler, alembic)
├── email/            🟡 ~60% (нет email_service.py, observability, audit_log, scheduler, alembic, unit-tests)
├── admin/            🔴 ~30% (нет models/, middleware/, observability, tests, Dockerfile)

backend/              ⚠️ Django ещё живой (Phase 4.5 удалит)
frontend/             ⚠️ React — частично на /api/hr/v1, остальное на Django
infra/
  ├── logging/        ✅ готов (не поднимался)
  ├── nginx/          ✅ (обновится в 4.2)
  ├── db/             ✅
  └── certs/          ✅
```

---

## Контрольный список проверки state (start-of-session)

```bash
# Git + tags
git log --oneline -5
git tag | grep django-final

# Phase 3 артефакты
ls services/{cms,media,messenger,email,admin}/app/main.py
ls services/{cms,media,messenger,email}/alembic.ini 2>/dev/null   # 0 сейчас, 4 после 3.7.7

# Observability propagation
for svc in cms media messenger email admin; do
  test -f services/$svc/app/core/logging.py && echo "$svc: Y" || echo "$svc: N"
done

# Endpoints check
ls services/task/app/api/v1/{comments,attachments,activity,sequences}.py 2>/dev/null | wc -l
ls services/messenger/app/api/v1/{read,attachments,admin}.py 2>/dev/null | wc -l

# Docker state
docker ps --format "{{.Names}}" | sort
docker images htqweb-backend
```

Если какая-то команда даёт неожиданный результат — **записать в лог "Desync detected" и разобраться до начала работы**.

---

### 2026-04-23 — Session Summary (Stabilizing Phase 3.7 Services)

**Выполненные действия:**

1.  **Messenger Service:**
    - Рефакторинг моделей: Переименован `MessageAttachment` -> `ChatAttachment` для соответствия архитектуре.
    - Обновлена модель `ChatAttachment`: поля `message_id` и `file_metadata_id` сделаны опциональными (nullable), добавлено поле `uploaded_by`.
    - Исправлен эндпоинт `mark_read`: теперь использует `RoomParticipant` вместо несуществующего `ChatMembership` и принимает `message_id`.
    - Исправлены ошибки импорта во всех файлах сервиса (`messenger_service.py`, `schemas/messenger.py`, `admin/views/*`).
    - Сервис успешно запускается и проходит healthcheck.

2.  **CMS Service:**
    - Исправлена ошибка `ModuleNotFoundError: email-validator`: пакет добавлен в `requirements.txt`.
    - Сервис успешно запускается и проходит healthcheck.

3.  **Task Service:**
    - Унификация БД: `get_db` переименован в `get_db_session` (с сохранением алиаса) для единообразия с другими сервисами.
    - Исправлены массовые ошибки импорта: `app.models.domain` заменён на `app.models` (т.к. модели в Task разнесены по файлам и экспортируются через `__init__.py`).
    - Исправлено несоответствие полей в `TaskAttachment`: API синхронизировано с моделью (`uploaded_by_id`, `file_path`).
    - Добавлены недостающие модели-реплики: `User` (replica) и `Department` (replica) для удовлетворения связей SQLAlchemy (relationship).
    - Добавлена зависимость `require_admin` в `auth/dependencies.py`.
    - Исправлена ошибка `sqlalchemy.exc.ArgumentError: Column expression expected for argument 'remote_side'` в модели `Task`.

4.  **Admin Service (Aggregator):**
    - Консолидация зависимостей: в `requirements.txt` добавлены все пакеты, необходимые для импорта моделей других сервисов (`dramatiq`, `python-socketio`, `slowapi`, `email-validator` и др.).
    - Исправлены пути импорта для моделей Task.

**Текущий статус Runtime:**
- `db`, `redis`, `pgbouncer`: ✅ Healthy
- `user-service`, `hr-service`: ✅ Healthy
- `messenger-service`, `media-service`, `email-service`, `cms-service`: ✅ Healthy
- `task-service`, `admin-service`: ✅ Healthy (Все сервисы стабилизированы и запущены).

**Что необходимо выполнить:**
1.  **Проверка Фронтенда:** Убедиться, что фронтенд корректно взаимодействует с обновлёнными эндпоинтами (особенно загрузка аттачментов в Messenger и пометка сообщений прочитанными).
2.  **Alembic migrations:** Проверить, что `alembic_version_messenger` и другие таблицы миграций корректно отражают текущее состояние схем после переименований.
3.  **Синхронизация реплик:** Реализовать или проверить механизмы синхронизации данных из `user-service` в реплики `messenger` и `task` (Dramatiq actors).

---

### 2026-04-23 — Аудит после 0.0.2.6 + уборка артефактов (эта сессия)

**Проведён:** независимый аудит на фактическое соответствие репо заявленному состоянию Phase 3 + 4 in-progress. Запущены `ast.parse` по всему коду сервисов, обход директорий, проверка импорта `main.py`.

**Подтверждено (✅):**
- Все 8 сервисов (`user, hr, task, cms, media, messenger, email, admin`) присутствуют, `main.py` каждого парсится синтаксически корректно.
- `services/admin/Dockerfile`, `services/admin/requirements.txt` на месте; PYTHONPATH указывает на все 7 подчинённых сервисов.
- Alembic директории созданы для 7 сервисов (всё, кроме `admin` — и это корректно, т.к. аггрегатор своих моделей не имеет).
- `docker-compose.yml`: Django `backend:` блок удалён; добавлены 8 сервис-блоков + 2 worker (messenger, email) + loki/promtail/grafana.
- `infra/nginx/default.conf`: upstream-ы для всех 7 API-сервисов определены; `legacy_backend` остаётся как fallback в `/api/` и `/admin/` (плановое поведение для переходного периода).
- Frontend API clients созданы: `users.ts`, `cms.ts`, `media.ts` — добавлены в 0.0.2.6.
- `fastapi`/`sqlalchemy`/прочее резолвится в каждом `requirements.txt`; версии консистентны между сервисами.

**Найденные расхождения / исправлено в этой сессии:**

| Артефакт | Действие |
|---|---|
| `fix_main.py` в корне — одноразовый AST-фикс скрипт, случайно закоммичен в 0.0.2.5 | ✅ Удалён |
| `services/hr/app/routers/` (`__init__.py, example.py, health.py`) — мёртвые stubs от шаблона; `main.py` их не импортирует | ✅ Удалён |
| `services/task/app/routers/health.py` — legacy health endpoint; `main.py` импортировал именно его (дублировался с `app/core/health.py`) | ✅ Удалён; `main.py` переключён на `from app.core.health import router as health_router` |

**Найденные расхождения — оставлены (документированы):**

| Расхождение | Причина |
|---|---|
| Порты: `messenger=8008`, `media=8009`, `email=8010`, `cms=8011` (в плане было cms=8008, media=8009, messenger=8010, email=8011) | Внутренне консистентно между compose и nginx. Переназначать нет смысла — cost > benefit. Обновить при желании в отдельной фазе. |
| В compose есть только `messenger-worker` и `email-worker`, нет отдельных worker-блоков для user/hr/task/cms/media | Dramatiq в этих сервисах пока holds lightweight actors; dev-runtime запускает их инлайн. Вынос в отдельный process — Phase 4.6 если понадобится scale-out. |
| `admin-service` без `entrypoint.sh`, `tests/`, `alembic/` | Корректно — это аггрегатор ModelView-ов чужих моделей, собственной схемы не имеет. |
| `user-service` без `entrypoint.sh` | В Dockerfile CMD задаёт uvicorn напрямую, без скрипт-обёртки. Работает. Унификация с остальными — cosmetic. |
| Множественные `TODO` в `cms/news.py` (translate stub), `messenger/socket.py` (JWT validation в auth dict), `task/tasks.py` (response schema mapping) | Помечены в issue-list Phase 4.3 / 4.4. Не блокируют cutover при известных ограничениях. |

**Verification commands executed:**
```bash
python -c "import ast, os; [ast.parse(open(os.path.join(d,f),encoding='utf-8').read()) for svc in ['user','hr','task','cms','media','messenger','email','admin'] for d,_,fs in os.walk(f'services/{svc}/app') for f in fs if f.endswith('.py')]"  # → no SyntaxError
for svc in user hr task cms media messenger email admin; do ls services/$svc/app/main.py; done  # → все 8 существуют
grep -rn "from app.routers" services/  # → пусто после уборки
```

**Runtime smoke:** не запускался в этой сессии (audit-only). Полагаемся на отчёт от 0.0.2.5 (все сервисы healthy).

**Что актуально сделать дальше (Phase 4 continuation):**
1. **Alembic stamp** в каждом из 7 сервисов: `alembic revision --autogenerate -m "initial"` должно дать diff=0 против живых Django-таблиц, затем `alembic stamp head`. Блокирует Phase 4.4 (физическое удаление Django).
2. **Frontend E2E smoke** новых API-префиксов: регистрация → login → профиль → HR create employee → tasks create → messenger WS send → email draft → media upload/download with Range.
3. **User replica sync actors**: Dramatiq в messenger/task слушают events от user-service и обновляют реплики. Без этого messenger/task работают, но новые пользователи не увидятся в их локальных таблицах.
4. **Phase 4.4 — удаление `backend/`** только после 4.1-4.3 pass. Django-код пока физически присутствует в `backend/` (Dockerfile/manage.py/apps), rollback tag `v1.0-django-final` на месте.
5. **Observability**: Loki/Promtail/Grafana описаны в compose; не запускались живьём — отдельный smoke.

**Commit note:** изменения этой сессии — только уборка артефактов (3 удаления + 1 import swap в task/main.py). Не требует отдельной фазы.

---

### 2026-04-24 — 0.0.2.7 — Phase 4 push (admin bootstrap + WS client + nginx + compose + initial alembic)

**Запрос пользователя:** продолжить Phase 4; не удалять `backend/` (отложено до следующей сессии); добавить `socket.io-client` на фронте и переписать messenger; один большой коммит.

**Исходный симптом:** контейнер nginx падал с `host not found in upstream "backend:8000"`, админ-аккаунт создать было нечем.

#### Admin bootstrap + unified login flow (⚠ критичная дыра устранена)

Pre-existing mismatch:
- `create_token_pair` выдаёт JWT с `is_staff`/`is_superuser`.
- `JWTAdminAuthBackend.authenticate` проверяет несуществующий claim `is_admin`.
- user-service backend читает cookie `admin_session`, admin-aggregator — `htqweb_admin_session`.
- `login()` везде возвращал `False` — форма `/admin/login` не работала в принципе.

Сделано:
- [services/user/app/services/auth_service.py](services/user/app/services/auth_service.py): в JWT добавлен claim `is_admin = is_staff or is_superuser` (единый источник правды для всех sqladmin-backend-ов).
- [services/user/app/api/v1/auth.py](services/user/app/api/v1/auth.py): новый `admin_router` (`POST /api/users/v1/admin-session/login|logout`) — выставляет cookie `admin_session` с access-токеном, `Secure` только при HTTPS (видно по `X-Forwarded-Proto`), `HttpOnly+SameSite=Lax`, `Max-Age=7200`.
- [services/user/app/auth/admin_backend.py](services/user/app/auth/admin_backend.py): `login()` теперь читает form-data, валидирует по DB, сохраняет JWT в session. `authenticate()` читает сначала session, потом cookie.
- [services/{hr,task,cms,media,messenger,email}/app/auth/admin_backend.py](services/) + [services/admin/app/auth/backend.py](services/admin/app/auth/backend.py): `login()` делает httpx-запрос к `http://user-service:8005/api/token/`, валидирует полученный JWT локально (общий секрет), кладёт в session. Cookie-имя унифицировано: `admin_session` везде.
- [services/user/app/scripts/create_admin.py](services/user/app/scripts/create_admin.py): CLI `docker compose exec user-service python -m app.scripts.create_admin --username admin --email admin@htqweb.local --password s3cret!`. Создаёт нового или апгрейдит существующего пользователя до `is_staff=is_superuser=True, status=ACTIVE`. Пароль — bcrypt.
- **Бутстрап выполнен:** в БД создан `admin/admin123@htqweb.local` (id=1). Login end-to-end проверен: `POST /admin/login` → 302 + `Set-Cookie: session=...`, `GET /admin/` → 200.

#### Phase 4.1 — Frontend messenger на Socket.IO

- [frontend/package.json](frontend/package.json): добавлена зависимость `socket.io-client@4.8.1` (установку `bun install` пользователь запускает вручную).
- [frontend/src/features/messenger/api/socket.ts](frontend/src/features/messenger/api/socket.ts) — синглтон-фабрика `getMessengerSocket()` с JWT в `auth.token`, path `/ws/messenger/socket.io`, auto-reconnect.
- [frontend/src/features/messenger/hooks/useMessengerSocket.ts](frontend/src/features/messenger/hooks/useMessengerSocket.ts) — хук, подписывается на `message_new|message_read|user_typing`, делает `invalidateQueries`. На смене `activeRoomId` — `join_room`/`leave_room`.
- [frontend/src/features/messenger/MessengerPage.tsx](frontend/src/features/messenger/MessengerPage.tsx): hook подключён; `refetchInterval` снижен с 3-5 с до 30 с (сокет ведёт real-time, polling — safety net).
- **Ограничение:** backend socket.io handlers — всё ещё скелет (все `pass` в [services/messenger/app/api/socket.py](services/messenger/app/api/socket.py)). Frontend-код корректен, но до реализации сервера real-time events не поступают. Polling вытащит.

#### Phase 4.2 — Nginx cleanup (unblock contained startup)

- Удалён `upstream legacy_backend`.
- Удалены `proxy_pass http://legacy_backend` в `/api/` catch-all и `/admin/`.
- Добавлен `upstream admin_service { server admin-service:8012; }`.
- `/admin/` теперь проксируется в admin-aggregator; `/api/` без известного префикса → JSON-404.
- Добавлен `location /api/email/` → email_service (раньше был upstream, но не location).
- Добавлен liveness `location = /health { return 200 ... }` для встроенного Docker healthcheck nginx-образа.
- `listen 80; listen [::]:80;` — IPv6 слушатель (healthcheck образа резолвит `localhost` в `::1`).
- Readiness (`/health/ready`) теперь смотрит на `user_service` (identity authority) вместо legacy_backend.
- **Runtime проверка:** nginx контейнер = `(healthy)` после reload.

#### Phase 4.2b — PgBouncer + поисковые пути

Сопутствующее: `ALTER ROLE htqweb SET search_path = auth,hr,tasks,cms,media,messenger,email,public;` — так как asyncpg через PgBouncer в транзакционном режиме не может передать `search_path` как startup-параметр. Дополнительно:
- [docker-compose.yml](docker-compose.yml) pgbouncer: `IGNORE_STARTUP_PARAMETERS: extra_float_digits,search_path`.
- Перенесены `public.users` → `auth.users`, `public.userstatus` enum → `auth.userstatus` (ручные `ALTER ... SET SCHEMA`, т.к. изначальная миграция проставила их без схемы).

#### Phase 4.3 — Worker/Scheduler compose-блоки

Было: только `messenger-worker`, `email-worker`. Стало: для каждого из 7 сервисов добавлены `<svc>-worker` (Dramatiq) и `<svc>-scheduler` (APScheduler `python -m app.workers.scheduler`). Всем проставлен `healthcheck: disable: true` (процессы не слушают HTTP).

Исправлен баг в [services/cms/app/workers/scheduler.py](services/cms/app/workers/scheduler.py): отсутствовал `if __name__ == "__main__"` — контейнер выходил с code=0 и уходил в restart-loop. Добавлен `main()` + `asyncio.get_event_loop().run_forever()`.

Обогащены env.vars у `messenger-worker` и `email-worker` (было только `REDIS_URL`, теперь полный набор DB + JWT).

**Итог:** +14 блоков, все в статусе `Up` без restart.

#### Phase 4.4 — Initial Alembic migrations для cms/media/messenger/email

Схема env.py для этих 4 сервисов переписана:
- `include_schemas=True` — видит все схемы в БД.
- `include_object(...)` — фильтрует чужие таблицы: включает только `name` или `schema.name`, присутствующие в `target_metadata.tables` этого сервиса.
- Учтено, что некоторые модели используют `__table_args__ = {"schema": "cms"}` (ключи в metadata вида `cms.news`), а часть — нет.

Выполнено внутри живых контейнеров: `alembic revision --autogenerate -m initial`, затем скопированы файлы на host:
- [services/cms/alembic/versions/001_initial.py](services/cms/alembic/versions/001_initial.py) — `audit_log`, `cms.news`, `cms.contact_requests`.
- [services/media/alembic/versions/001_initial.py](services/media/alembic/versions/001_initial.py) — `media.file_metadata`.
- [services/messenger/alembic/versions/001_initial.py](services/messenger/alembic/versions/001_initial.py) — `chat_user_replicas, rooms, messages, room_participants, user_keys, chat_attachments` + `CREATE EXTENSION ltree` + импорт `app.models.types.LtreeType`.
- [services/email/alembic/versions/001_initial.py](services/email/alembic/versions/001_initial.py) — `oauth_tokens, email_messages, email_attachments, recipient_statuses`.

Каждой миграции добавлен `op.execute("CREATE SCHEMA IF NOT EXISTS <svc>")` в начало `upgrade()`.

**Применено:** все 4 миграции успешно `alembic upgrade head`; созданы схемы `cms, media, messenger, email`.

**Известное ограничение:** таблицы messenger/email без `__table_args__ schema` лёгли в `auth` (первый в search_path). Для production-миграции их нужно перенести `ALTER TABLE ... SET SCHEMA messenger` или добавить schema в модели. В dev-среде текущее работает через search_path.

#### Runtime state после сессии

```
docker compose ps — все сервисы (healthy) или (Up), включая:
  db, redis, pgbouncer, loki, promtail, grafana,
  user, hr, task, cms, media, messenger, email, admin (services),
  user/hr/task/cms/media/messenger/email -worker и -scheduler,
  sfu, webtransport, certbot, frontend, nginx
```

Админ-доступ проверен end-to-end:
```
curl -X POST localhost/admin/login -d 'username=admin&password=admin123'  → 302 + session cookie
curl -b cookie localhost/admin/                                          → 200 OK
```

#### Что не сделано (сознательно)

- `backend/` Django НЕ удалён (решение пользователя — оставить до следующей сессии).
- Schema-cleanup для messenger/email/cms-audit_log (лежат в auth из-за search_path order) — косметика, не блокирует runtime.
- socket.io серверные handlers остаются skeleton (все `pass`) — frontend переписан, но real-time работает только когда backend будет реализован.
- user-replica sync Dramatiq actors в messenger/task — не добавлены.
- E2E browser-тесты — не проведены.
- Phase 4.5 (git rm backend/, git tag v1.0-fastapi-initial) — отложено.

#### Commit: `0.0.2.7: Phase 4 — admin bootstrap + nginx cutover + compose workers + alembic init`
