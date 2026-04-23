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
| 3.2 cms-service | ⬜ pending | — | — |
| 3.3 media-service | ⬜ pending | — | — |
| 3.6 task-service endpoints | ⬜ pending | — | — |
| 3.4 messenger-service | ⬜ pending | — | — |
| 3.5 email-service | ⬜ pending | — | — |
| 3.X admin-aggregator | ⬜ pending | — | — |
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

### 2026-04-23 — `0.0.2.3` — Phase 0.5 + 0.6

**Commit:** `fc722e4` / tag `v1.0-django-final` (на предыдущий `e58493f`)

**Сделано:**
- `git tag v1.0-django-final` на `e58493f`
- `docker build -f backend/Dockerfile -t htqweb-backend:django-final backend/` (exit 0)
- удалены рекурсивно `backend/**/__pycache__/` (303 `.pyc`)
- удалены `backend/db.sqlite3`, `backend/django_error.log`
- удалены untracked `.md` в корне: `CHEATSHEET.md`, `DEPLOY.md`, `QUICK_FIX.md`, `READY_TO_RUN.md`, `SUMMARY.md`, `WEBRTC_AUDIT.md`, `WEBRTC_ANALYSIS.md`, `WEBRTC_TROUBLESHOOTING.md`
- сохранены: `docs/HR_SERVICE_TECHNICAL_SPEC.md`, `services/*/README.md` (теперь в git)
- **docker-compose.yml** — добавлены сервисы:
  - `loki` (grafana/loki:2.9.10, порт 3100, volume `loki_data`)
  - `promtail` (grafana/promtail:2.9.10, монтирует `/var/lib/docker/containers` + `/var/run/docker.sock`)
  - `grafana` (grafana/grafana-oss:10.4.4, порт 3001, volume `grafana_data`)
- **infra/logging/**:
  - `loki-config.yml` — single-binary, filesystem storage, retention 336h
  - `promtail-config.yml` — Docker SD + JSON pipeline (вытаскивает `level`, `event`, `correlation_id`)
  - `grafana-provisioning/datasources/loki.yml`
  - `grafana-provisioning/dashboards/htqweb.yml`
  - `grafana-dashboards/htqweb-services-overview.json` (error rate + recent errors + log rate panels)
- **services/_template/**:
  - `app/core/logging.py` (новый) — structlog JSON + `STANDARD_EVENTS` + `configure_logging()` + `get_logger()`
  - `app/middleware/request_id.py` (обновлён) — читает/пробрасывает `X-Correlation-ID`, биндит в structlog contextvars
  - `app/middleware/request_logging.py` (новый) — `request_received` / `request_completed` / `request_failed` с duration_ms
  - `app/models/base.py` (новый) — `DeclarativeBase`, `TimestampMixin`, `IntIdMixin`
  - `app/models/audit_log.py` (новый) — `AuditLog(Base)`, JSONB `changes`, indexed `correlation_id`, `action`, `resource_id`
  - `app/services/audit.py` (новый) — `async record_action(session, user_id, action, resource_type, resource_id, changes, request)`
  - `app/models/__init__.py` экспорт `Base, AuditLog, TimestampMixin, IntIdMixin`
  - `app/main.py` — подключает `configure_logging()` в `create_app()`, middleware chain: `RequestLoggingMiddleware` (outer) → `RequestIDMiddleware` (inner)
- синтаксис всех новых `.py` проверен через `ast.parse`

**Непроверено / требует валидации (TODO при первом запуске сервиса):**
- `docker compose up loki promtail grafana` — не запускалось; не подтверждено что Grafana видит Loki datasource
- `_template/main.py` не запущен в uvicorn; только syntax-check
- `promtail-config.yml` pipeline: не проверено что `json` stage корректно парсит реальные logs (зависит от точного формата structlog output)
- AuditLog table в БД не создан — будет в Phase 4.4 через Alembic
- OTEL instrumentation не добавлена в `_template/main.py` (есть только в `services/user/` частично) — отложено на Phase 5.6

**Отклонения от плана (dynamic-imagining-goblet.md):**
- ❌ Пропущен `scripts/dev/run-all.sh` (0.6.5) — некритично, dev-удобство
- ❌ Пропущен `infra/logging/deploy.sh` (0.6.5) — deploy log sentinel, можно добавить в Phase 5.8
- ❌ Пропущен `tempo` service для traces (0.6.4) — OTEL остаётся stdout-exporter
- ⚠️ `_template/app/core/settings.py` НЕ обновлён — новые поля (`oauth_encryption_key`, `storage_backend`, `translation_api_key`, FCM/APNS) добавим per-service в их собственных settings.py

**Следующий шаг:** Phase 3.2 — cms-service.
- Источники: `backend/media_manager/models.py`, `backend/media_manager/views.py`, `backend/mainView/views.py`
- Старт: заменить плейсхолдеры в `services/cms/app/main.py` (`__service_name__` → `cms`)
- Deliverables: модели News/ContactRequest, schemas, endpoints, admin, workers (translate_news stub, news_scheduled_publish), YAML conference, slowapi rate-limit, pytest + testcontainers

---

## Известное состояние репозитория (на момент последнего обновления)

```
services/
├── _template/        ✅ канонический, обновлён в 0.0.2.3 с observability
├── user/             ✅ готов (Phase 3.1, до сессии)
├── hr/               ✅ готов (Phase 3.7, до сессии)
├── task/             🟡 модели+admin+workers есть, но endpoints НЕ портированы (Phase 3.6)
├── cms/              🟡 только scaffold (~15%, placeholder'ы)
├── media/            ⬜ нет
├── messenger/        ⬜ нет
├── email/            ⬜ нет
└── admin/            ⬜ нет

backend/              ⚠️ Django ещё живой, удалится в Phase 4.4
  └── hr, internal_email, mainView, media_manager, messenger, tasks, webtransport, HTQWeb

frontend/             ⚠️ React — частично мигрирован на /api/hr/v1, остальное на Django API
infra/
  ├── nginx/          ✅ есть
  ├── db/             ✅ есть (init-ltree.sql)
  ├── certs/          ✅ есть
  └── logging/        ✅ новое (0.0.2.3)
```

---

## Контрольный список проверки state (выполнить в начале следующей сессии)

```bash
# State проверка
git log --oneline -3              # ожидаем: fc722e4 0.0.2.3 ... → e58493f 0.0.2.2 ...
git tag | grep django-final       # ожидаем: v1.0-django-final
docker images htqweb-backend      # ожидаем: htqweb-backend:django-final

# Структура проверка
ls services/_template/app/core/logging.py      # должен существовать
ls services/_template/app/models/audit_log.py  # должен существовать
ls infra/logging/loki-config.yml               # должен существовать

# CMS на стартовой линии
ls services/cms/app/models/                    # пока только __init__.py
grep '__service_name__' services/cms/app/main.py  # ещё есть placeholder'ы
```

Если какая-то команда даёт неожиданный результат — **записать в лог Desync detected и разобраться до начала работы.**
