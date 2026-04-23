# PLAN.md — Execution log миграции HTQWeb (Django → FastAPI)

> **Источник истины (полный план):** `C:\Users\User\.claude\plans\dynamic-imagining-goblet.md`
> **Этот файл** — живой журнал выполнения. Обновляется **после каждой завершённой фазы** одновременно с git-коммитом. Предотвращает рассинхрон контекста между сессиями (anti-hallucination container).

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
| **3 (bulk) cms/media/messenger/email/admin + task endpoints** | 🟡 **partial (с пробелами)** | `2f93153` (0.0.2.4) | — |
| **3.7 Fill Phase 3 gaps** | ⬜ pending | — | — |
| 4 Cutover (frontend + Alembic + rm Django) | ⬜ pending | — | — |
| 5 Post-production audit | ⬜ pending | — | `v1.0-fastapi-production` (в конце) |

---

## Ключевые решения (зафиксировано до старта)

Зафиксированы через AskUserQuestion в сессии планирования 2026-04-23:

- **Режим:** big-bang до Phase 4.5 (+ Phase 5), но пошаговые коммиты после каждой фазы
- **CMS news.translate** — Dramatiq actor + внешний API TODO через env
- **CMS conference config** — YAML `app/data/conference.yaml`
- **Media storage** — `aiofiles` (local) для dev/early-prod, `aioboto3` (S3) переключение через `STORAGE_BACKEND` env
- **Messenger WS** — `python-socketio` + Redis adapter (НЕ нативный FastAPI WS)
- **Email OAuth** — env-плейсхолдеры, endpoints 503 при пустых ключах
- **Alembic** — autogenerate должен давать diff=0 против живых Django-таблиц, затем `stamp head`
- **Admin UI** — единый `services/admin/` (агрегатор) с импортом моделей через PYTHONPATH
- **Messenger attachments** — локально в messenger-service
- **Rollback** — `git tag v1.0-django-final` + `docker image htqweb-backend:django-final` (оба созданы)
- **Logging** — Loki + Promtail + Grafana self-hosted (в docker-compose)
- **Audit log** — таблица `audit_log` в схеме каждого сервиса + поток в Loki
- **Тесты** — pytest + testcontainers (реальный Postgres); unit + integration + E2E (Playwright)

---

## Лог изменений (reverse chronological)

### 2026-04-23 — `0.0.2.4` — Phase 3 bulk (внешняя сессия)

**Commit:** `2f93153` (121 файлов, +6322 / −99). Выполнен в отдельном окружении, перенесён в репозиторий.

**Проверено через фактический аудит репозитория (не по словам того, кто делал):**

#### 3.2 cms-service — ✅ ~90% done
Структура соответствует плану, сервис почти готов к smoke-запуску.
- ✅ models: `news`, `contact_request`, `audit_log`, `base` + `__init__.py` экспорт
- ✅ schemas: `news`, `contact_request`, `conference` + `__init__.py` экспорт
- ✅ endpoints: `api/v1/{news,contact_requests,conference}.py`
- ✅ admin: `admin/views/{news,contact_request}.py`
- ✅ workers: `actors.py` + `scheduler.py` (news_scheduled_publish)
- ✅ `app/data/conference.yaml` заполнен
- ✅ `auth/dependencies.py` с `require_admin` / `get_optional_user`
- ✅ observability: `core/logging.py`, `middleware/request_logging.py`, `request_id.py` (с correlation_id)
- ✅ тесты: `conftest.py` + 2 unit (`test_news_schema`, `test_scheduler_query`) + 3 integration (`test_conference`, `test_contact_requests_api`, `test_news_api`)
- **Gap:** нет выделенных `test_audit_log.py`, `test_translate_actor.py` (покрытие может быть в existing test_news_api — надо проверить), нет `alembic/`

#### 3.3 media-service — 🟡 ~60% done
Скелет и основные пути есть, но тесты и workers неполные.
- ✅ `storage.py` — абстракция + LocalStorage + S3Storage + factory
- ✅ `models/file_metadata.py` + `audit_log.py` + `base.py`
- ✅ `api/v1/files.py` (upload/download/...)
- ✅ `admin/views/file_metadata.py`
- ✅ `auth/{admin_backend,dependencies}.py`
- ✅ `core/logging.py`, `middleware/request_id.py`
- **Gap:** `middleware/request_logging.py` ❌
- **Gap:** нет unit-тестов (плани требовал `test_local_storage`, `test_s3_storage`, `test_range_parser`, `test_path_traversal`); только 1 integration file (`test_files_api.py`)
- **Gap:** `workers/scheduler.py` ❌ (нет `cleanup_orphan_files` APScheduler-job)
- **Gap:** `alembic/` ❌

#### 3.4 messenger-service — 🟡 ~55% done
Socket.IO поднят, 4 REST endpoint-а есть, но существенные пропуски.
- ✅ `api/socket.py` — Socket.IO AsyncServer
- ✅ `api/v1/{rooms, messages, users, keys}.py` (4 из 7 запланированных)
- ✅ `models/{domain, types, base}.py` — 6 моделей DDD (упрощённо в `domain.py` единым файлом)
- ✅ `models/types.py` — LtreeType
- ✅ `schemas/messenger.py`
- ✅ `services/messenger_service.py`
- ✅ `admin/__init__.py` + `admin/views.py`
- ❌ **Missing endpoints:** `api/v1/read.py` (mark-read REST), `api/v1/attachments.py` (файл-upload), `api/v1/admin.py` (admin rooms list)
- ❌ **Missing observability:** нет `core/logging.py`, НЕТ `middleware/` директории вообще (нет `request_id.py` ни `request_logging.py`)
- ❌ **Missing audit:** нет `models/audit_log.py`, нет `services/audit.py`
- ❌ **Missing workers:** нет `scheduler.py` (плани требовал `archive_old_messages`, `cleanup_presence`); actor `dispatch_push_notification` — надо проверить в actors.py
- ❌ **Simplified admin:** один файл `views.py` вместо 6 отдельных ModelView-модулей
- ❌ **Missing application layer:** не разделено на `send_message/mark_read/publish_typing` use-cases
- ❌ **main.py** не подключает health_router явно (возможно через Socket.IO mount — требует верификации)
- ❌ **Tests:** 1 integration file (`test_messenger_api.py`); нет unit-тестов для ltree / next_pts / WS-protocol
- ❌ `alembic/` ❌

#### 3.5 email-service — 🟡 ~60% done
Криптография + DLP + MTA портированы, но orchestration и тесты слабые.
- ✅ `models/email.py` (все 4 таблицы в одном файле) + `base.py`
- ✅ `api/v1/{emails, oauth}.py`
- ✅ `services/{crypto, dlp_scanner, mta_connector}.py` — AES-256-GCM, 3 DLP-паттерна, SMTP/IMAP
- ✅ `schemas/email.py`
- ✅ `admin/{__init__, views}.py`
- ✅ `workers/{__init__, actors}.py`
- ❌ **Missing services:** нет `services/oauth.py` (OAuth, возможно, inline в api/v1/oauth.py — приемлемо)
- ❌ **Missing services:** нет `services/email_service.py` (orchestration use-case: DLP.check → atomic create → enqueue deliver_email)
- ❌ **Missing observability:** нет `core/logging.py`, нет `middleware/` директории
- ❌ **Missing audit:** нет `models/audit_log.py`, нет `services/audit.py`
- ❌ **Missing scheduler:** нет `workers/scheduler.py` (плани требовал `mta_inbound_poll`, `oauth_token_refresh`)
- ❌ **Tests:** 1 integration file; нет unit для crypto/dlp/mta (критические модули — план требовал ≥75% coverage)
- ❌ `alembic/` ❌

#### 3.X admin-aggregator — 🔴 ~30% done
Скелет + dynamic imports в main.py, но инфраструктура не завершена.
- ✅ `app/main.py` — создаёт FastAPI + Admin + делает `sys.path.insert(base_dir)` + try/except импорт ModelView из всех сервисов
- ✅ `app/auth/backend.py` — JWTAdminAuthBackend
- ✅ `app/core/settings.py`, `app/db.py`, `requirements.txt`
- ❌ **Missing:** `app/models/__init__.py` (нет пакета для cross-service models; сейчас полагается на пути `user.app.admin.views...` что хрупко)
- ❌ **Missing:** выделенный `app/admin/__init__.py` (логика в main.py с try/except — silently skips failures)
- ❌ **Missing:** observability (`core/logging.py`, `middleware/`, `audit_log`)
- ❌ **Missing:** `Dockerfile` (для настройки PYTHONPATH через ENV)
- ❌ **Missing:** `.env.example`
- ❌ **Tests:** 0 файлов тестов

#### 3.6 task-service endpoints — 🟡 ~55% done
Добавлены 6 endpoint-модулей и calendar-модель, но не все.
- ✅ `api/v1/__init__.py` агрегирует 6 роутеров под префиксом `/api/tasks/v1`
- ✅ `api/v1/{tasks, labels, versions, links, notifications, calendar}.py`
- ✅ модели уже были: task, comment, attachment, link, label, notification, version, activity, sequence + **добавлено** `models/calendar.py`
- ✅ `schemas/calendar.py`
- ✅ `alembic/` есть (был до 3.6)
- ❌ **Missing endpoints:** `api/v1/{comments, attachments, activity, sequences}.py` (4 из 10 запланированных)
- ❌ **Missing services:** `services/calendar.py` (O(1) working_days_since_epoch) — план требовал выделенного calendar-service
- ❌ **Missing services:** `services/sequences.py` (атомарная генерация TASK-X)
- ❌ **Tests:** 1 integration file; нет unit для calendar math / sequence atomicity / contract vs Django

### Cross-cutting issues (inherit в Phase 3.7)

| Issue | Затронутые сервисы | Критичность |
|---|---|---|
| Нет `alembic/` | cms, media, messenger, email, admin | 🔴 блокирует Phase 4.4 |
| Нет observability (`core/logging.py`, `middleware/request_logging.py`) | messenger, email, admin | 🟠 снижает ценность Loki-стека |
| Нет `models/audit_log.py` + `services/audit.py` | messenger, email, admin | 🟠 требование заказчика |
| Нет `workers/scheduler.py` | media, messenger, email | 🟠 `audit_log_compaction` не запускается, feature-gaps |
| Недостающие endpoints | task (4), messenger (3) | 🟠 фронт не сможет вызвать некоторые пути |
| Unit-тесты почти отсутствуют | все кроме cms | 🟡 Phase 5 всё равно требует coverage ≥70% |
| admin-aggregator неполон | admin | 🔴 /admin/ не заработает из-за хрупких импортов |

### Проверено (факт)
- `git log --oneline` подтверждает коммит `2f93153`.
- `ast.parse` по всем новым `.py` — **все парсятся без синтаксических ошибок**.
- `git tag` — `v1.0-django-final` на месте.
- `ls services/` — все 8 сервисов присутствуют (user, hr, task, cms, media, messenger, email, admin + _template).
- `services/cms/app/data/conference.yaml` существует и заполнен.

### Непроверено / требует runtime-валидации
- Запуск `uvicorn` ни для одного из новых сервисов не выполнялся.
- `docker compose up` для новых сервисов не пробовался.
- pytest (даже для cms с 5 тест-файлами) не прогонялся — есть риск что testcontainers или импорты не работают.
- Loki+Promtail+Grafana не поднимались — не подтверждено что observability-стек функционален.
- Socket.IO handshake не тестировался.
- Ни одна Alembic миграция не применялась к БД (даже в сервисах где alembic/ есть).

---

### 2026-04-23 — `c35abd1` — PLAN.md → execution log

**Commit:** `c35abd1`

Преобразовал PLAN.md из статического плана в живой журнал с протоколом anti-hallucination. Никаких изменений кода.

---

### 2026-04-23 — `0.0.2.3` — Phase 0.5 + 0.6

**Commit:** `fc722e4` / tag `v1.0-django-final` (на предыдущий `e58493f`)

**Сделано:**
- `git tag v1.0-django-final` на `e58493f`
- `docker build -f backend/Dockerfile -t htqweb-backend:django-final backend/` (exit 0)
- удалены рекурсивно `backend/**/__pycache__/` (303 `.pyc`), `backend/db.sqlite3`, `backend/django_error.log`
- удалены untracked `.md` в корне (CHEATSHEET, DEPLOY, QUICK_FIX, READY_TO_RUN, SUMMARY, WEBRTC_*)
- **docker-compose.yml** — добавлены сервисы `loki` (3100), `promtail`, `grafana` (3001) + volumes
- **infra/logging/**: loki-config, promtail-config, Grafana provisioning, базовый dashboard
- **services/_template/** observability: `core/logging.py`, обновлённый `middleware/request_id.py` (с correlation_id), новый `middleware/request_logging.py`, `models/base.py`, `models/audit_log.py`, `services/audit.py`, экспорт в `models/__init__.py`, `main.py` подключает всё

**Непроверено:** реальный запуск observability-стека не выполнялся.

---

## 📋 Phase 3.7 — Fill Phase 3 gaps (план следующей фазы)

**Цель:** довести Phase 3 сервисы до состояния, при котором можно надёжно перейти к Phase 4 cutover. Без этой фазы Phase 4 провалится (alembic, admin-aggregator, отсутствующие endpoints).

**Оценка:** 1 большая сессия или 2 средних. ~80 файлов.

### 3.7.1 Observability propagation (блокирует: audit требования)
Скопировать из `services/_template/` в messenger, email, admin:
- `app/core/logging.py`
- `app/middleware/request_id.py` (с correlation_id)
- `app/middleware/request_logging.py`
- `app/models/base.py` (если есть конфликт — мержить)
- `app/models/audit_log.py`
- `app/services/audit.py`
- Обновить `models/__init__.py` — экспорт `Base`, `AuditLog`
- Обновить `main.py` — `configure_logging()` + `RequestLoggingMiddleware` + `RequestIDMiddleware`

Также media: добавить `request_logging.py`.

### 3.7.2 Messenger missing endpoints + workers + observability
- `api/v1/read.py` — POST `/rooms/{id}/read/`
- `api/v1/attachments.py` — POST `/attachments/upload/` (локальный storage)
- `api/v1/admin.py` — GET `/admin/rooms/`, GET `/admin/rooms/{id}/messages/`
- `application/{send_message,mark_read,publish_typing}.py` — use-cases
- `workers/scheduler.py` — `archive_old_messages`, `cleanup_presence`, `audit_log_compaction`
- `workers/actors.py` — добавить `dispatch_push_notification` если не готов
- Разделить `admin/views.py` на 6 отдельных файлов (ChatUserReplicaAdmin, ChatRoomAdmin, ChatMembershipAdmin, EncryptedMessageAdmin, AuthKeyBundleAdmin, ChatAttachmentAdmin)
- Unit-тесты: `test_ltree_fields.py`, `test_next_pts.py`, `test_websocket.py` (через python-socketio AsyncClient)

### 3.7.3 Email missing services + workers + unit-тесты
- `services/oauth.py` — вынести httpx-клиент из `api/v1/oauth.py` (если там всё inline)
- `services/email_service.py` — orchestration `send_email`: DLP → atomic create → enqueue
- `workers/scheduler.py` — `mta_inbound_poll` (60s), `oauth_token_refresh` (30min), `audit_log_compaction`
- `workers/actors.py` — убедиться что есть `deliver_email` с `Retries(max_retries=5)`, `dlp_scan_attachment`
- Unit-тесты: `test_crypto.py` (encrypt/decrypt round-trip + tamper), `test_dlp.py` (3 паттерна), `test_mta_sanitize.py` (CRLF injection)

### 3.7.4 Media missing scheduler + unit-тесты
- `workers/scheduler.py` — `cleanup_orphan_files` (еженедельно) + `audit_log_compaction`
- Unit-тесты: `test_local_storage.py`, `test_s3_storage.py` (через `moto`), `test_range_parser.py`, `test_path_traversal.py`

### 3.7.5 Task missing endpoints + services + unit-тесты
- `api/v1/{comments,attachments,activity,sequences}.py` — 4 endpoint-модуля
- Добавить их в `api/v1/__init__.py` aggregator
- `services/calendar.py` — O(1) `working_days_since_epoch` helper
- `services/sequences.py` — атомарная `next_task_key(project)` через `SELECT ... FOR UPDATE`
- Unit-тесты: `test_calendar.py`, `test_sequences.py`

### 3.7.6 Admin-aggregator завершить
- `app/Dockerfile` с `ENV PYTHONPATH=/services/user:/services/hr:...`
- `app/models/__init__.py` — явный import Base из каждого сервиса + merge MetaData (если нужно)
- `app/admin/__init__.py` — вынести регистрацию ModelView из `main.py`
- `app/middleware/`, `app/core/logging.py` — observability
- `.env.example`
- Tests: `test_imports.py`, `test_admin_auth.py`, `test_cross_service_models.py`

### 3.7.7 Alembic init для 5 сервисов (блокирует Phase 4.4)
Для каждого из `cms, media, messenger, email, admin`:
1. `alembic init alembic` (ровно как в user/hr/task)
2. `alembic.ini` — `sqlalchemy.url = ${DB_DSN}` через env
3. `alembic/env.py` — `target_metadata = Base.metadata`, `version_table_schema = settings.db_schema`
4. **НЕ запускать** autogenerate/upgrade сейчас — это Phase 4.4 против живой Django-БД.
5. Только подготовить инфраструктуру.

### 3.7.8 Runtime smoke
После всех файлов — по каждому сервису:
- `uvicorn app.main:app --port <port>` должен стартовать без exceptions
- `curl /health/` → 200
- `curl /docs` → HTML OpenAPI
- pytest — минимум зелёный на testcontainers

### 3.7.9 Обновить PLAN.md и коммит
Коммит: `0.0.2.5: phase 3.7 fill gaps (observability propagation, missing endpoints, alembic init)`

---

## Phase 4 — Cutover (revised после Phase 3.7)

Остаётся в основном как в [dynamic-imagining-goblet.md](C:\Users\User\.claude\plans\dynamic-imagining-goblet.md), но:

- **4.1 Frontend refactor** — дождаться завершения 3.7, иначе фронт будет ломаться на отсутствующих endpoints (task/comments, messenger/read).
- **4.2 Nginx** — без изменений.
- **4.3 docker-compose.yml** — без изменений.
- **4.4 Alembic stamp** — только если 3.7.7 alembic init выполнен. Процедура:
  1. `alembic revision --autogenerate` против живой БД
  2. Верифицировать что diff **пустой** (самый рискованный шаг; план требует итеративной доводки модели пока diff=0)
  3. `alembic stamp head`
- **4.5 Удалить Django** — без изменений.

## Phase 5 — Post-production audit (revised)

Целевые метрики coverage ≥70% может быть нереалистичным после 3.7 в один заход — закладываем 2 итерации:
1. **5.0 (первый проход):** ruff, mypy, bandit, pip-audit — быстрые правки. Coverage baseline без fill.
2. **5.1–5.9 (по плану):** playwright, perf, error-path, security.

---

## Известное состояние репозитория (на момент 2f93153)

```
services/
├── _template/        ✅ канонический (с observability из 0.0.2.3)
├── user/             ✅ готов (Phase 3.1, до сессий)
├── hr/               ✅ готов (Phase 3.7 старой нумерации)
├── task/             🟡 модели+admin+workers+alembic+6 endpoint-ов; НЕ хватает 4 endpoints + 2 services + unit-тестов
├── cms/              ✅ ~90% (нет alembic, нет dedicated audit-tests)
├── media/            🟡 ~60% (нет scheduler, unit-tests, alembic)
├── messenger/        🟡 ~55% (нет 3 endpoints, middleware/, logging, audit_log, scheduler, alembic)
├── email/            🟡 ~60% (нет email_service orchestrator, middleware/, logging, audit_log, scheduler, alembic, unit-tests)
├── admin/            🔴 ~30% (нет models/ aggregation, middleware/, observability, tests, Dockerfile)
└── _template/        ✅ (обновлён в 0.0.2.3)

backend/              ⚠️ Django ещё живой, удалится в Phase 4.4
frontend/             ⚠️ React — частично мигрирован
infra/
  ├── logging/        ✅ (0.0.2.3) — Loki/Promtail/Grafana конфиги готовы, не поднимались
  ├── nginx/          ✅
  ├── db/             ✅
  └── certs/          ✅
```

---

## Контрольный список проверки state (выполнить в начале следующей сессии)

```bash
# Git state
git log --oneline -5              # ожидаем: 2f93153 0.0.2.4 Phase 3 complete → c35abd1 docs:... → fc722e4 0.0.2.3 ...
git tag | grep django-final       # v1.0-django-final
docker images htqweb-backend      # htqweb-backend:django-final

# Phase 3 артефакты
ls services/{cms,media,messenger,email,admin}/app/main.py  # все 5 существуют
ls services/{cms,media,messenger,email,admin}/alembic.ini 2>/dev/null   # все 5 должны отсутствовать (добавятся в 3.7.7)

# Observability propagation
test -f services/cms/app/core/logging.py && echo "cms: Y"         # ожидаем Y
test -f services/messenger/app/core/logging.py && echo "msg: Y" || echo "msg: N"   # ожидаем N (будет Y после 3.7)
test -f services/email/app/core/logging.py && echo "email: Y" || echo "email: N"   # ожидаем N
test -f services/admin/app/core/logging.py && echo "admin: Y" || echo "admin: N"   # ожидаем N

# Endpoints наличие
ls services/task/app/api/v1/{comments,attachments,activity,sequences}.py 2>/dev/null | wc -l   # 0 сейчас, 4 после 3.7
ls services/messenger/app/api/v1/{read,attachments,admin}.py 2>/dev/null | wc -l  # 0 сейчас, 3 после 3.7
```

Если какая-то команда даёт неожиданный результат — **записать в лог Desync detected и разобраться до начала работы.**
