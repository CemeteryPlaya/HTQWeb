# PLAN.md — План дальнейших работ HTQWeb (Django → FastAPI)

> **Источник истины (исходный план):** `C:\Users\User\.claude\plans\piped-gliding-perlis.md`
> **Этот файл** — детализированный журнал оставшихся задач и пошаговая инструкция к ним. Обновляется после каждой завершённой фазы одновременно с git-коммитом.

---

## Протокол ведения (обязательно для каждой сессии)

**В начале сессии:**
1. Прочитать этот файл целиком.
2. `git log --oneline -10` — последний коммит совпадает с таблицей ниже?
3. `git tag` — `v1.0-django-final` на месте?
4. `ls services/` — 8 сервисов + `_template` существуют?
5. `docker compose ps` — все сервисы `(healthy)`? Если нет — поднять и диагностировать до работы.
6. При расхождении — зафиксировать в логе в конце файла «Desync detected» и только потом работать.

**Перед началом подфазы:**
- Пометить в таблице `🟡 in_progress`.
- Прочитать relevant раздел этого файла полностью — в нём уже расписаны file paths, commands, verification.

**После коммита подфазы:**
- Таблица: `✅ done` + hash коммита.
- Заполнить секцию лога честно (что реально сделано, пропуски, riski).
- Никогда не удалять старые записи — только добавлять.

---

## Статус по коммитам (что уже сделано)

| Фаза | Состояние | Коммит | Tag |
|---|---|---|---|
| 0.5 Cleanup + rollback tag | ✅ done | `fc722e4` (0.0.2.3) | `v1.0-django-final` |
| 0.6 Observability bootstrap (Loki/Promtail/Grafana добавлены в compose) | ✅ done | `fc722e4` | — |
| 3 (bulk) 8 сервисов + admin-aggregator + frontend API clients | ✅ done | `2f93153` (0.0.2.4) | — |
| 3.7 Fill Phase 3 gaps (observability, scheduler, middleware) | ✅ done | `56bb6a0` (0.0.2.5) | — |
| 4.0 Frontend API clients + nginx upstream + compose services | ✅ done | `e4635e9` (0.0.2.6) | — |
| 4.1 Admin bootstrap + nginx cutover + compose workers/schedulers + initial alembic | ✅ done | `d673393` (0.0.2.7) | — |
| 4.2 Hotfix sqladmin `/admin/` → `/sqladmin/` + dev compose fix | ✅ done | `27faf38` (0.0.2.8) | — |
| 4.3 Unify user-service API prefixes + HTTP-only Vite + simplify proxy | ✅ done | `847d8fa` (0.0.2.9) | — |
| 4.4 Fix post-login crash (profile response shape + frontend paths) | ✅ done | `1a66fed` (0.0.3.0) | — |
| 4.5 Backend endpoint backfill + pre-deploy comprehensive logging | ✅ done | `b7c37e9` (0.0.3.2) | — |
| 4.5.1 Cut dev TLS: SFU/certbot/webtransport → production profile, Vite HTTP-only | ✅ done | pending commit `0.0.3.3` | — |
| **4.6 Data migration from Django tables into service schemas** | ⬜ pending | — | — |
| **4.7 Schema cleanup (move stray tables into proper schemas)** | ⬜ pending | — | — |
| **4.8 Удалить `backend/` (Django)** | ⬜ pending | — | `v1.0-fastapi-initial` |
| **5.1 Messenger Socket.IO серверная реализация** | ⬜ pending | — | — |
| **5.2 User-replica sync actors (Dramatiq)** | ⬜ pending | — | — |
| **5.3 Dev ergonomics (HMR, Vite config sanity)** | ⬜ pending | — | — |
| **5.4 Observability smoke (Loki+Promtail+Grafana)** | ⬜ pending | — | — |
| **6.1 Testing infrastructure + coverage** | ⬜ pending | — | — |
| **6.2 Static analysis (ruff + mypy + bandit)** | ⬜ pending | — | — |
| **6.3 Dependency audit** | ⬜ pending | — | — |
| **7.1 E2E browser smoke (регистрация/login/hr/tasks/messenger/email/media)** | ⬜ pending | — | — |
| **7.2 Production cutover (nginx prod, HTTPS, certbot)** | ⬜ pending | — | — |
| **7.3 Runbook + Backup strategy + Alerts** | ⬜ pending | — | — |
| **7.4 Финальный tag `v1.0-fastapi-production`** | ⬜ pending | — | `v1.0-fastapi-production` |

---

## Что уже работает (зафиксировано на 0.0.3.0)

- 8 FastAPI-сервисов `(healthy)` в dev compose:
  `user:8005, hr:8006, task:8007, messenger:8008, media:8009, email:8010, cms:8011, admin:8012`
- PgBouncer + Postgres + Redis + Loki/Promtail/Grafana.
- Для каждого прикладного сервиса: worker (Dramatiq) и scheduler (APScheduler).
- nginx на `:80` (prod mode), Vite dev server на `:3000` (dev mode, HTTP).
- Единый API-namespace: `/api/<service>/v1/*` для каждого сервиса.
- sqladmin агрегатор на `/sqladmin/` — **не конфликтует** с SPA-маршрутами `/admin/users`, `/admin/chats`, `/admin/registrations`.
- Admin-flow: `admin/admin123` → `POST /sqladmin/login` → session cookie → `/sqladmin/` dashboard.
- Login flow: `POST /api/users/v1/token/` → JWT (claim `is_admin = is_staff OR is_superuser`).
- Alembic initial migrations применены для всех 7 сервисов со своей схемой.

---

# ═══════════════════════════════════════════════════════════
# Phase 4.5 — Backend endpoint backfill
# ═══════════════════════════════════════════════════════════

**Цель.** Фронт зовёт endpoint-ы, которых нет в FastAPI. Каждый такой 404 = регрессия по отношению к Django. Нужно реализовать недостающие endpoint-ы 1:1.

**Оценка:** 2–4 часа. Один коммит на каждый endpoint или bundle.

## 4.5.1 `POST /api/users/v1/profile/change-password/`

**Используется из:** [frontend/src/components/ForcePasswordChange.tsx:19](frontend/src/components/ForcePasswordChange.tsx#L19)

**Шаги:**

1. В [services/user/app/api/v1/profile.py](services/user/app/api/v1/profile.py) добавить:
   ```python
   class ChangePasswordRequest(BaseModel):
       new_password: str
       current_password: str | None = None  # None when must_change_password=True (forced change)

   @router.post("/change-password", status_code=204)
   async def change_password(
       request: ChangePasswordRequest,
       current_user: Annotated[TokenPayload, Depends(get_current_user)],
       db: Annotated[AsyncSession, Depends(get_db_session)],
   ):
       result = await db.execute(select(User).where(User.id == current_user.user_id))
       user = result.scalar_one_or_none()
       if not user:
           raise HTTPException(404, "User not found")

       # If user must change password (HR-forced), current_password is optional.
       if not user.must_change_password:
           if not request.current_password or not verify_password(request.current_password, user.password_hash):
               raise HTTPException(400, "Current password is incorrect")
       if len(request.new_password) < 8:
           raise HTTPException(400, "Password must be at least 8 characters")

       user.password_hash = hash_password(request.new_password)
       user.must_change_password = False
       await db.commit()
   ```
2. Импорты: `from app.services.auth_service import verify_password, hash_password`, `from app.auth.dependencies import TokenPayload, get_current_user`.
3. Verification:
   ```bash
   docker compose build user-service && docker compose up -d user-service
   TOKEN=$(curl -s -X POST http://localhost:8005/api/users/v1/token/ \
     -H 'Content-Type: application/json' \
     -d '{"email":"admin@htqweb.local","password":"admin123"}' | jq -r .access)
   curl -si -X POST http://localhost:8005/api/users/v1/profile/change-password \
     -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"new_password":"new_pw_123","current_password":"admin123"}'
   # → 204 No Content
   # Verify: next login with admin123 fails, with new_pw_123 succeeds
   ```
4. Commit: `0.0.3.1: user-service change-password endpoint`.

## 4.5.2 Avatar upload — `PATCH /api/users/v1/profile/me` с multipart/form-data

**Проблема.** Сейчас PATCH принимает JSON. [frontend/src/pages/MyProfile.tsx:50](frontend/src/pages/MyProfile.tsx#L50) шлёт `FormData` с `avatar: File`.

**Решения (выбрать одно):**

**Вариант A (рекомендуется).** Обновить PATCH-хендлер в [profile.py](services/user/app/api/v1/profile.py):
- Принимать `multipart/form-data` через `Form` + `File` параметры:
  ```python
  @router.patch("/me", response_model=ProfileResponse)
  @router.patch("/", response_model=ProfileResponse)
  async def update_profile(
      current_user: Annotated[TokenPayload, Depends(get_current_user)],
      db: Annotated[AsyncSession, Depends(get_db_session)],
      display_name: Annotated[str | None, Form()] = None,
      firstName: Annotated[str | None, Form()] = None,
      lastName: Annotated[str | None, Form()] = None,
      patronymic: Annotated[str | None, Form()] = None,
      bio: Annotated[str | None, Form()] = None,
      phone: Annotated[str | None, Form()] = None,
      settings: Annotated[str | None, Form()] = None,  # JSON string
      avatar: Annotated[UploadFile | None, File()] = None,
  ):
      ...
      if avatar and avatar.filename:
          # Upload to media-service via httpx
          async with httpx.AsyncClient() as client:
              resp = await client.post(
                  f"{settings.media_service_url}/api/media/v1/upload",
                  files={"file": (avatar.filename, await avatar.read(), avatar.content_type)},
                  headers={"Authorization": f"Bearer {service_token}"},
              )
              user.avatar_url = resp.json()["url"]
      ...
  ```

**Вариант B.** Отдельный endpoint `POST /api/users/v1/profile/avatar` принимающий только multipart — проще в реализации, но требует правки фронта (сейчас фронт шлёт всё в один PATCH).

**Шаги (Вариант A):**

1. Добавить в [services/user/app/core/settings.py](services/user/app/core/settings.py) поле `media_service_url: str = "http://media-service:8009"`.
2. Реализовать авторизацию между сервисами — временно через service-to-service JWT, выпущенный user-service самому себе (claim `sub: "user-service"`). Долгосрочно — выделить отдельный `SERVICE_JWT_SECRET` или использовать mTLS.
3. В [services/media/app/api/v1/files.py](services/media/app/api/v1/files.py) убедиться что `POST /api/media/v1/upload` существует и принимает `file` в multipart (проверить — возможно нужно допилить).
4. Добавить `httpx` в требованиях user-service (уже есть).
5. Verification:
   ```bash
   echo "test" > /tmp/avatar.jpg
   curl -si -X PATCH http://localhost:8005/api/users/v1/profile/me \
     -H "Authorization: Bearer $TOKEN" \
     -F 'display_name=Admin Root' \
     -F 'avatar=@/tmp/avatar.jpg'
   # → 200 + response с avatarUrl заполненным
   ```
6. Commit: `0.0.3.2: user-service multipart profile update + avatar upload`.

## 4.5.3 Public CMS endpoints: contact-requests, conference/config

**Используется из:**
- [frontend/src/components/ContactSection.tsx:94](frontend/src/components/ContactSection.tsx#L94) — `POST /api/cms/v1/contact-requests/` (публичный, без JWT)
- [frontend/src/pages/ConferencePage.tsx:501](frontend/src/pages/ConferencePage.tsx#L501) — `GET /api/cms/v1/conference/config`

**Шаги:**

1. Проверить, что в [services/cms/app/api/v1/contact_requests.py](services/cms/app/api/v1/contact_requests.py) `POST /` публичный (без Depends(get_current_user)) и с rate-limit через `slowapi` (3/min).
2. Проверить [services/cms/app/api/v1/conference.py](services/cms/app/api/v1/conference.py) — возвращает YAML-конфиг в JSON. Frontend ожидает поля `conference_config_runtime` (см. типы в [frontend/src/types/](frontend/src/types/)).
3. В [services/cms/app/main.py](services/cms/app/main.py) убедиться что роутеры зарегистрированы с корректным prefix.
4. Verification:
   ```bash
   curl -si -X POST http://localhost:8011/api/cms/v1/contact-requests/ \
     -H 'Content-Type: application/json' \
     -d '{"email":"test@ex.com","first_name":"Test","message":"hi"}'
   # → 201 Created (публичный)

   curl -si http://localhost:8011/api/cms/v1/conference/config
   # → 200 + JSON с полями rtp_capabilities, ice_servers и т.д.
   ```
5. Commit: `0.0.3.3: verify public CMS endpoints`.

## 4.5.4 ProfileSidebar quick fixes

[frontend/src/components/profile/ProfileSidebar.tsx](frontend/src/components/profile/ProfileSidebar.tsx) делает 2 запроса при монтировании для админа:
- `GET /api/cms/v1/contact-requests/stats/` — возвращает `{total, unread, ...}` для badge.
- `GET /api/users/v1/pending-registrations/` — для badge `N`.

**Шаги:**
1. Проверить что оба endpoint-а существуют.
2. Для `contact-requests/stats/` — реализовать в cms-service, если нет (`COUNT(*) WHERE handled = FALSE`).
3. Обернуть компонент в `.length ?? 0` если массив может быть undefined.

---

# ═══════════════════════════════════════════════════════════
# Phase 4.6 — Data migration from Django tables
# ═══════════════════════════════════════════════════════════

**Цель.** Сейчас новые микросервисные таблицы пустые. Django ещё имеет данные (если в прошлом была production-инстанция; при «fresh» разработке данных нет — тогда эта фаза пропускается). Перенести все существующие записи в service schemas.

**КРИТИЧНО.** Перед запуском снять полный pg_dump:
```bash
docker compose exec db pg_dump -U htqweb htqweb > backup-pre-migration-$(date -u +%Y%m%dT%H%M%SZ).sql
```

**Оценка:** 4–8 часов, зависит от объёма данных.

## 4.6.1 Предварительная инвентаризация

Запустить внутри контейнера db:
```sql
-- Проверить, какие Django-таблицы ещё содержат данные:
SELECT schemaname, tablename, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND tablename ~ '^(auth_|mainView_|hr_|tasks_|messenger_|internal_email_|media_manager_)'
ORDER BY n_live_tup DESC;
```

Записать результат в `docs/migration-inventory-$(date -u +%Y%m%d).md`.

## 4.6.2 Per-table migration

**Таблица соответствий Django → service schema:**

| Django (public) | Service.schema.table | Колоночные маппинги |
|---|---|---|
| `auth_user` | `auth.users` | id 1:1, username, email, password_hash (check Django PBKDF2 format — verify_password уже умеет оба), first_name/last_name 1:1 |
| `mainView_profile` | `auth.users` (merge) | bio, phone, avatar_url, patronymic, display_name, settings (JSON) |
| `mainView_item` | `auth.items` (? — проверить, мы добавляли модель Item в user-service) | id, title, description, owner_id FK, created_at |
| `mainView_news` | `cms.news` | id, title, slug, summary, content, image, category, published, published_at, created_at |
| `mainView_contactrequest` | `cms.contact_requests` | id, first_name, last_name, email, message, handled, replied_at, replied_by_id, reply_message, created_at |
| `mainView_conferenceconfig` | **не мигрируем** — config теперь в YAML [services/cms/app/data/conference.yaml](services/cms/app/data/conference.yaml) |
| `hr_*` (12 таблиц) | `public.hr_*` (уже есть) | Проверить — возможно уже мигрированы через `0.0.2.5`. Если данные расходятся — руками `INSERT INTO ... SELECT ...` |
| `tasks_*` | `public.task_*` | Аналогично — проверить миграцию |
| `messenger_*` (6 таблиц) | `messenger.*` | Сейчас таблицы в `auth` (из-за search_path). Сначала `ALTER TABLE auth.X SET SCHEMA messenger` — Phase 4.7 |
| `internal_email_*` (4 таблицы) | `email.*` | То же — таблицы в `auth`. Сначала 4.7. |
| `media_manager_*` | `media.file_metadata` | Если есть metadata — мигрировать. Сами файлы уже в media-volume. |

## 4.6.3 Пример миграции: News

1. Написать миграцию [services/cms/alembic/versions/002_import_django_news.py](services/cms/alembic/versions/002_import_django_news.py):
   ```python
   """Import Django mainView_news into cms.news"""
   revision = '002'
   down_revision = '001'

   def upgrade():
       op.execute("""
           INSERT INTO cms.news (id, title, slug, summary, content, image, category, published, published_at, created_at)
           SELECT id, title, slug, summary, content, image, category, published, published_at, created_at
           FROM public.mainView_news
           ON CONFLICT (id) DO NOTHING
       """)
       # Update sequence to max(id)+1 to avoid collisions on new inserts
       op.execute("SELECT setval('cms.news_id_seq', COALESCE((SELECT MAX(id) FROM cms.news), 1) + 1)")

   def downgrade():
       op.execute("TRUNCATE cms.news RESTART IDENTITY CASCADE")
   ```
2. Применить:
   ```bash
   docker compose exec cms-service sh -c "cd /app && PYTHONPATH=/app alembic -c alembic.ini upgrade head"
   ```
3. Verify:
   ```sql
   SELECT count(*) FROM cms.news;
   SELECT count(*) FROM public.mainView_news;
   -- Должны совпадать.
   ```

## 4.6.4 Повторить для каждой таблицы

- Создать migration-скрипты 002_import_*.py в каждом сервисе.
- Применить по порядку: `user → cms → hr → task → media → messenger → email`.
- После каждого шага — SELECT count-check.

## 4.6.5 Coммит
```bash
git commit -m "0.0.3.X: phase 4.6 data migration from Django tables"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 4.7 — Schema cleanup (move stray tables)
# ═══════════════════════════════════════════════════════════

**Проблема.** Некоторые модели messenger/email/cms не имеют `__table_args__ = {"schema": "..."}` — при миграции они легли в `auth` (первый в search_path для роли `htqweb`).

**Проверка:**
```sql
\dt auth.*
-- Увидим chat_*, room_*, message*, email_*, oauth_tokens — они должны быть в messenger.*, email.*
```

## 4.7.1 Fix models (чтобы новые инсталляции сразу писали в нужную схему)

Пройтись по моделям и добавить `__table_args__`:
- [services/messenger/app/models/](services/messenger/app/models/) — 6 моделей
- [services/email/app/models/](services/email/app/models/) — 4 модели
- [services/cms/app/models/audit_log.py](services/cms/app/models/audit_log.py) — 1 модель
- [services/media/app/models/audit_log.py](services/media/app/models/audit_log.py) — 1 модель
- [services/hr/app/models/audit_log.py](services/hr/app/models/audit_log.py) — 1 модель
- [services/task/app/models/audit_log.py](services/task/app/models/audit_log.py) — 1 модель

Пример:
```python
class ChatRoom(Base):
    __tablename__ = "rooms"
    __table_args__ = {"schema": "messenger"}
```

## 4.7.2 Migration 003 — физически перенести таблицы

Для каждого сервиса (messenger, email) создать [services/<svc>/alembic/versions/003_move_to_own_schema.py](services/):
```python
def upgrade():
    op.execute("ALTER TABLE IF EXISTS auth.rooms SET SCHEMA messenger")
    op.execute("ALTER TABLE IF EXISTS auth.messages SET SCHEMA messenger")
    op.execute("ALTER TABLE IF EXISTS auth.room_participants SET SCHEMA messenger")
    op.execute("ALTER TABLE IF EXISTS auth.chat_attachments SET SCHEMA messenger")
    op.execute("ALTER TABLE IF EXISTS auth.chat_user_replicas SET SCHEMA messenger")
    op.execute("ALTER TABLE IF EXISTS auth.user_keys SET SCHEMA messenger")
    # Foreign keys, sequences follow the table automatically
```

## 4.7.3 Скорректировать search_path роли

Сейчас `ALTER ROLE htqweb SET search_path = auth,hr,tasks,cms,media,messenger,email,public` — это костыль. Лучше НЕ включать чужие схемы, а в `db.py` каждого сервиса передавать `server_settings.search_path = <svc-schema>`.

**Шаги:**
1. В каждом `db.py` задать `search_path = f"{settings.db_schema},public"` (уже делается, но проверить).
2. На БД: `ALTER ROLE htqweb SET search_path = "$user", public` (вернуть дефолт).
3. Перезапустить все сервисы. Проверить что `SELECT * FROM users` внутри каждого сервиса всё ещё работает (должен, т.к. connection-level search_path перекрывает role-level).

## 4.7.4 Verification

```sql
\dt auth.*       -- Должно быть: alembic_version, users (и только).
\dt messenger.*  -- 6 таблиц
\dt email.*      -- 4 таблицы
\dt cms.*        -- 3 (audit_log, news, contact_requests)
```

## 4.7.5 Commit

```bash
git commit -m "0.0.3.X: phase 4.7 schema cleanup — table_args + migration 003 move_to_own_schema"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 4.8 — Удалить Django (финальный cutover)
# ═══════════════════════════════════════════════════════════

**Предусловия:**
- 4.5, 4.6, 4.7 закоммичены и проверены.
- E2E smoke (Phase 7.1) прошёл хотя бы вручную.
- Созданы бэкапы: git tag `v1.0-django-final`, image `htqweb-backend:django-final`.

## 4.8.1 Удаление файлов

```bash
git rm -r backend/HTQWeb/
git rm -r backend/hr/ backend/internal_email/ backend/mainView/ backend/media_manager/ backend/messenger/ backend/tasks/
git rm backend/manage.py backend/requirements.txt backend/entrypoint.sh backend/Dockerfile
git rm -rf backend/webtransport/   # если перенесли в top-level webtransport/
# Papka backend/media/ — если данные в S3/volume уже доступны media-service, можно удалить.
# Иначе временно оставить.
```

## 4.8.2 Финал docker-compose / .env

- Убрать упоминания `backend:` и `VITE_BACKEND_*` из [docker-compose.dev.yml](docker-compose.dev.yml), [.env*](.env).
- Удалить корневой [Dockerfile](Dockerfile) если он был для Django.

## 4.8.3 Удалить Django служебные таблицы из БД

```sql
DROP TABLE IF EXISTS public.django_migrations;
DROP TABLE IF EXISTS public.django_content_type;
DROP TABLE IF EXISTS public.django_admin_log;
DROP TABLE IF EXISTS public.django_session;
DROP TABLE IF EXISTS public.auth_permission;
DROP TABLE IF EXISTS public.auth_group_permissions;
DROP TABLE IF EXISTS public.auth_group;
DROP TABLE IF EXISTS public.auth_user_groups;
DROP TABLE IF EXISTS public.auth_user_user_permissions;
-- auth_user уже должен быть перенесён в auth.users (4.6)
DROP TABLE IF EXISTS public.auth_user;
-- Django-таблицы mainView_* — данные уже перенесены в cms.*/auth.*
DROP TABLE IF EXISTS public.mainView_profile;
DROP TABLE IF EXISTS public.mainView_item;
DROP TABLE IF EXISTS public.mainView_news;
DROP TABLE IF EXISTS public.mainView_contactrequest;
DROP TABLE IF EXISTS public.mainView_conferenceconfig;
DROP TABLE IF EXISTS public.media_manager_file;
-- Аналогично для hr_*, tasks_*, messenger_*, internal_email_* если они дубли service-таблиц
```

## 4.8.4 Commit + tag

```bash
git commit -m "0.1.0: phase 4.8 cutover complete — Django removed"
git tag v1.0-fastapi-initial
# Tag `v1.0-django-final` остаётся — это точка возврата.
```

## 4.8.5 Rollback (если cutover сломан)

```bash
git checkout v1.0-django-final
docker compose up -d --build
# + восстановить БД из pg_dump
docker compose exec -T db psql -U htqweb htqweb < backup-pre-migration-*.sql
```

---

# ═══════════════════════════════════════════════════════════
# Phase 5.1 — Messenger Socket.IO серверная реализация
# ═══════════════════════════════════════════════════════════

**Проблема.** [services/messenger/app/api/socket.py](services/messenger/app/api/socket.py) — все handlers `pass`. Frontend (`useMessengerSocket`) уже ждёт события `message_new, message_read, user_typing`. Real-time не работает.

**Оценка:** 4–6 часов.

## 5.1.a JWT validation в `connect`

```python
@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token")
    if not token:
        raise socketio.exceptions.ConnectionRefusedError("missing_token")
    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError:
        raise socketio.exceptions.ConnectionRefusedError("invalid_token")
    await sio.save_session(sid, {
        "user_id": payload["user_id"],
        "username": payload["username"],
    })
    logger.info("socket connected", extra={"sid": sid, "user_id": payload["user_id"]})
```

## 5.1.b Join/leave room с проверкой membership

```python
@sio.event
async def join_room(sid, data):
    session = await sio.get_session(sid)
    user_id = session["user_id"]
    room_id = data.get("room_id")
    # Проверить что user — участник комнаты
    async with async_session_factory() as db:
        result = await db.execute(
            select(RoomParticipant).where(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            return {"error": "not_a_member"}
    sio.enter_room(sid, f"room:{room_id}")
    return {"ok": True}
```

## 5.1.c Emit `message_new` при создании message через REST

В [services/messenger/app/api/v1/messages.py](services/messenger/app/api/v1/messages.py):
- После `await db.commit()` в `POST /messages/`:
  ```python
  from app.api.socket import sio
  await sio.emit(
      "message_new",
      {"room_id": room_id, "message": serialize(msg)},
      room=f"room:{room_id}",
  )
  ```

## 5.1.d `message_read` + `typing` handlers

```python
@sio.event
async def mark_read(sid, data):
    session = await sio.get_session(sid)
    room_id = data["room_id"]
    message_id = data["message_id"]
    # UPDATE room_participants SET last_read_message_id = ... WHERE user_id = ... AND room_id = ...
    await sio.emit(
        "message_read",
        {"room_id": room_id, "message_id": message_id, "reader_user_id": session["user_id"]},
        room=f"room:{room_id}",
        skip_sid=sid,
    )

@sio.event
async def typing(sid, data):
    session = await sio.get_session(sid)
    await sio.emit(
        "user_typing",
        {"room_id": data["room_id"], "user_id": session["user_id"], "is_typing": data.get("is_typing", True)},
        room=f"room:{data['room_id']}",
        skip_sid=sid,
    )
```

## 5.1.e Верификация

1. Browser DevTools → Network → filter WS → открыть /messenger → должен быть `ws://.../socket.io/?...` upgrade 101.
2. Открыть два вкладки под разными юзерами → отправить сообщение → приходит `message_new` в другой вкладке без F5.

## 5.1.f Commit

```bash
git commit -m "0.0.4.0: messenger socket.io — JWT validation + room membership + message_new/read/typing"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 5.2 — User-replica sync actors
# ═══════════════════════════════════════════════════════════

**Проблема.** Messenger и task сервисы имеют свои локальные реплики User (ChatUserReplica, task.user_replica). Когда юзер создаётся в user-service, эти реплики не обновляются → новый юзер невидим в чате и в задачах.

## 5.2.a User-service emits event on user create/update

В [services/user/app/api/v1/registration.py](services/user/app/api/v1/registration.py) (после approve):
```python
from app.workers.actors import user_upserted

# После db.commit():
user_upserted.send({
    "id": user.id,
    "username": user.username,
    "email": user.email,
    "first_name": user.first_name,
    "last_name": user.last_name,
    "display_name": user.display_name,
    "avatar_url": user.avatar_url,
    "status": user.status.value,
})
```

В [services/user/app/workers/actors.py](services/user/app/workers/actors.py) добавить actor `user_upserted` который ничего сам не делает — просто публикует в Redis pub/sub:
```python
@dramatiq.actor(max_retries=3)
def user_upserted(payload: dict):
    import redis
    r = redis.Redis.from_url(settings.redis_url)
    r.publish("user.upserted", json.dumps(payload))
    logger.info("user.upserted published", extra={"user_id": payload["id"]})
```

## 5.2.b Messenger/task подписываются на pub/sub

В [services/messenger/app/workers/actors.py](services/messenger/app/workers/actors.py) (или отдельным background task-ом):
```python
async def user_replica_sync_loop():
    """Subscribe to user.upserted events and upsert ChatUserReplica rows."""
    import redis.asyncio as aioredis
    r = aioredis.Redis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe("user.upserted")
    async for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        payload = json.loads(msg["data"])
        async with async_session_factory() as db:
            replica = await db.get(ChatUserReplica, payload["id"])
            if replica:
                for k in ("username", "email", "display_name", "avatar_url"):
                    setattr(replica, k, payload.get(k))
            else:
                db.add(ChatUserReplica(
                    id=payload["id"],
                    username=payload["username"],
                    email=payload["email"],
                    display_name=payload.get("display_name") or "",
                    avatar_url=payload.get("avatar_url"),
                ))
            await db.commit()
```

Запустить в [main.py](services/messenger/app/main.py) lifespan:
```python
@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(user_replica_sync_loop())
    yield
    task.cancel()
```

## 5.2.c Аналогично для task-service

[services/task/app/workers/actors.py](services/task/app/workers/actors.py) — свой `user_replica_sync_loop` для `task.user_replica` и `task.department_replica`.

## 5.2.d Bootstrap initial sync

Actor `rebuild_user_replicas` — одноразовая команда которая вытаскивает ВСЕХ юзеров из user-service через `GET /api/users/v1/admin/users/` и upsert-ит в локальные реплики:
```python
@dramatiq.actor
def rebuild_user_replicas():
    import httpx
    resp = httpx.get(f"{settings.user_service_url}/api/users/v1/admin/users/",
                     headers={"Authorization": f"Bearer {service_token}"})
    for u in resp.json():
        upsert_replica(u)
```

Run:
```bash
docker compose exec messenger-worker python -c "from app.workers.actors import rebuild_user_replicas; rebuild_user_replicas.send()"
```

## 5.2.e Commit

```bash
git commit -m "0.0.4.1: user-replica sync — Redis pub/sub + initial rebuild actor"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 5.3 — Dev ergonomics
# ═══════════════════════════════════════════════════════════

## 5.3.a Enable HMR in dev compose

[frontend/.env](frontend/.env) имеет `VITE_DISABLE_HMR=true` (от старой ngrok-эры). В dev-compose override:

[docker-compose.dev.yml](docker-compose.dev.yml) — в блоке `frontend.environment:`:
```yaml
VITE_DISABLE_HMR: "false"
```

Verify: сохранение файла `.tsx` → браузер автообновляется без F5.

## 5.3.b Sanity для `vite.config.ts`

Удалить мёртвые ENV-переменные (`VITE_BACKEND_HTTP_TARGET`, `VITE_BACKEND_WS_TARGET` — больше не используются после 0.0.2.9).

## 5.3.c Зафиксировать `VITE_DEV_HTTPS=false` в frontend/.env

(По умолчанию сейчас `=true` — наследие старой настройки. Лучше явно указать HTTP-only для dev-mode.)

## 5.3.d Commit

```bash
git commit -m "0.0.4.2: dev ergonomics — enable HMR, clean up Vite env vars"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 5.4 — Observability smoke
# ═══════════════════════════════════════════════════════════

Loki/Promtail/Grafana добавлены в compose в 0.0.2.3, но ни разу не поднимались живьём.

## 5.4.a Проверить что контейнеры стартуют

```bash
docker compose up -d loki promtail grafana
docker compose ps | grep -E "loki|promtail|grafana"  # все (healthy)
```

## 5.4.b Grafana UI

Открыть http://localhost:3001 → login `admin/admin` → смена пароля → навигация Connections → Data sources → убедиться что Loki добавлен (провижинится автоматически через [infra/logging/grafana/provisioning/](infra/logging/grafana/provisioning/)).

## 5.4.c Проверить сбор логов

Grafana → Explore → Data source: Loki → Label `container_name=~"htqweb-.*"` → Run query. Должны появиться логи всех сервисов.

## 5.4.d Готовый dashboard

[infra/logging/grafana/dashboards/](infra/logging/grafana/dashboards/) — открыть базовый. Проверить что панели показывают rate/error counts.

## 5.4.e Добавить alert

В Grafana → Alerting → New alert rule:
- Condition: `count_over_time({level="ERROR"}[5m]) > 10`
- Notify: email/slack/webhook — выбрать что есть под рукой.

## 5.4.f Commit

```bash
git commit -m "0.0.4.3: observability smoke — Grafana dashboards + error alert rule"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 6.1 — Testing infrastructure
# ═══════════════════════════════════════════════════════════

**Сейчас:**
- `services/cms/tests/` — conftest + unit + integration
- `services/email/tests/, media/tests/, messenger/tests/, task/tests/` — только conftest (без integration)
- `services/user/tests/, hr/tests/, admin/tests/` — нет вообще

**Цель.** Каждый сервис имеет unit + integration тесты. Coverage > 60% на критических путях (auth, crypto, DLP, payments если есть).

## 6.1.a Базовый test-suite для каждого сервиса

Создать в services/`{user,hr,admin}`/tests/:
```
conftest.py     — pytest fixtures (testcontainers Postgres, httpx client)
unit/           — unit-tests для services/, schemas/
integration/    — API-tests через httpx AsyncClient (реальный DB через testcontainers)
```

## 6.1.b Критичные сценарии (must-have)

**user-service:**
- POST /api/users/v1/token/ happy path → 200 + JWT
- POST /api/users/v1/token/ wrong password → 401
- POST /api/users/v1/register/ → 201, PENDING status
- GET /api/users/v1/profile/me (with JWT) → 200 + профиль
- POST /api/users/v1/profile/change-password → 204
- POST /api/users/v1/admin-session/login → 303 + Set-Cookie admin_session

**hr-service:**
- POST /employees (admin JWT) → 201
- GET /departments → 200 + tree

**task-service:**
- POST /tasks → 201 + key (e.g. TASK-1)
- GET /tasks/calendar → 200

**messenger-service:**
- POST /rooms → 201
- POST /messages → 201 + ack
- WS: connect + join_room + message_new emit cycle

**email-service:**
- DLP scanner unit tests — позитивные и негативные примеры
- crypto.encrypt_decrypt roundtrip

## 6.1.c Run

```bash
cd services/user && pytest --cov=app --cov-report=term-missing
# Повторить для каждого
```

## 6.1.d CI workflow (отложено до репозитория с GitHub Actions)

`.github/workflows/test.yml`:
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:16 }
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db redis pgbouncer
      - run: for svc in user hr task cms media messenger email admin; do cd services/$svc && pytest; done
```

## 6.1.e Commit

```bash
git commit -m "0.1.1: test infrastructure — unit + integration tests per service"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 6.2 — Static analysis
# ═══════════════════════════════════════════════════════════

## 6.2.a ruff

```bash
pip install ruff==0.8.4
ruff check services/ --select E,F,W,I,UP,N
ruff format services/
```

В каждом `services/<svc>/pyproject.toml` уже есть `[tool.ruff]` секция — выровнять.

Цель: 0 errors, 0 unformatted files.

## 6.2.b mypy

```bash
pip install mypy==1.13.0
for svc in user hr task cms media messenger email admin; do
  cd services/$svc
  mypy app/ --strict-optional --ignore-missing-imports --check-untyped-defs 2>&1 | tee ../../docs/mypy-$svc-$(date -u +%Y%m%d).log
  cd ../..
done
```

Цель: **ноль `error:`** в auth/, crypto/, dlp_scanner/, payments/ (если есть).

## 6.2.c bandit

```bash
pip install bandit==1.8.0
bandit -r services/ -ll -ii -f json -o docs/bandit-$(date -u +%Y%m%d).json
```

Цель: **ноль `severity=HIGH`**. `MEDIUM` — разобрать каждый, решение задокументировать.

## 6.2.d Commit

```bash
git commit -m "0.1.2: static analysis fixes — ruff + mypy + bandit"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 6.3 — Dependency audit
# ═══════════════════════════════════════════════════════════

## 6.3.a Python

```bash
pip install pip-audit==2.7.3
for svc in user hr task cms media messenger email admin; do
  cd services/$svc
  pip-audit -r requirements.txt --format json > ../../docs/pip-audit-$svc-$(date -u +%Y%m%d).json
  cd ../..
done
```

HIGH → обновить пакет, перепроверить.

## 6.3.b Frontend

```bash
cd frontend
npm audit --audit-level=high --json > ../docs/npm-audit-$(date -u +%Y%m%d).json
npm audit fix
```

## 6.3.c Dependabot

`.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/services/cms"
    schedule: { interval: "weekly" }
  # ... для каждого services/<svc>
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule: { interval: "weekly" }
```

## 6.3.d Commit

```bash
git commit -m "0.1.3: dependency audit + auto-update config"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 7.1 — E2E browser smoke
# ═══════════════════════════════════════════════════════════

Набор сценариев, проверяемых вручную или через Playwright.

## 7.1.a Сценарии

1. **Регистрация.** http://localhost:3000 → Register → email+password → сабмит → статус PENDING → admin approves → login.
2. **Login.** admin/admin123 → /myprofile открывается без crash. Aватар плейсхолдер. `roles = [admin]`.
3. **Profile edit.** Сменить display_name → refresh → сохранилось.
4. **HR.** /hr/employees → список → создать нового сотрудника → deparment ассайн.
5. **Tasks.** /tasks → создать → перетащить по канбан → изменить статус → календарь показывает дедлайн.
6. **Messenger.** /messenger → создать чат → отправить текст → открыть другое окно под другим юзером → сообщение приходит real-time без F5.
7. **Email.** /email/inbox → создать draft → отправить (на свой же email).
8. **Media.** /files → upload файл → скачать (проверить Range через `curl --range 0-1023`).
9. **sqladmin.** /sqladmin/ → login → каждая ModelView открывается и показывает данные.
10. **Conference/SFU.** /conference → запустить звонок → WebRTC handshake.

## 7.1.b Playwright тесты (опционально)

`frontend/tests/e2e/`:
```ts
test("login + profile", async ({ page }) => {
  await page.goto("http://localhost:3000/login");
  await page.fill('input[name="email"]', "admin");
  await page.fill('input[name="password"]', "admin123");
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/myprofile/);
  await expect(page.getByText("admin@htqweb.local")).toBeVisible();
});
```

## 7.1.c Commit

```bash
git commit -m "0.1.4: E2E browser smoke — all critical flows verified"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 7.2 — Production cutover (HTTPS + domain)
# ═══════════════════════════════════════════════════════════

**Только когда приложение поднимается публично (у нас есть реальный domain и сервер).**

## 7.2.a Certbot + Let's Encrypt

```bash
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot -d htqweb.example.com \
  --email admin@htqweb.example.com --agree-tos
```

## 7.2.b Раскомментировать HTTPS-блок в [infra/nginx/default.conf](infra/nginx/default.conf)

- Строки 484–630 сейчас закомментированы. Раскомментировать, заменить `YOUR_DOMAIN` на реальный.
- Добавить `return 301 https://$host$request_uri;` в HTTP-блоке (80).

## 7.2.c Cron для обновления серта

```bash
echo "0 3 * * * docker compose run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload" \
  | crontab -
```

## 7.2.d Secure cookies

В [services/user/app/api/v1/auth.py](services/user/app/api/v1/auth.py) админ-сессия уже `secure=is_https` — проверить, что `X-Forwarded-Proto: https` форвардится nginx-ом.

## 7.2.e Commit

```bash
git commit -m "0.1.5: HTTPS cutover — Let's Encrypt + nginx SSL + secure cookies"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 7.3 — Runbook + Backup + Alerts
# ═══════════════════════════════════════════════════════════

## 7.3.a `docs/runbook.md`

Разделы:
1. **Архитектура** — диаграмма сервисов, портов, зависимостей.
2. **Deploy** — `docker compose up -d --build`.
3. **Scale** — `docker compose up --scale <service>=3`.
4. **Debug one request** — X-Request-ID лог-поиск через Grafana.
5. **Common failures** → actions:
   - pgbouncer unhealthy → `docker compose restart pgbouncer`
   - Redis OOM → `docker compose logs redis` + `CONFIG SET maxmemory-policy`
   - user-service 500 → `docker compose logs user-service --tail=100`
   - DLP false positive → `docker compose exec email-worker python -c "..."`
6. **Rollback** — `git checkout v1.0-django-final && docker compose up -d --build`.

## 7.3.b Backup

`docs/backup.md`:
```
## Daily DB backup (cron на host)
0 2 * * * docker compose exec -T db pg_dump -U htqweb htqweb | gzip > /backups/htqweb-$(date -u +\%Y\%m\%d).sql.gz
# Retention 30 days:
0 3 * * * find /backups -name "htqweb-*.sql.gz" -mtime +30 -delete

## Volume snapshots (weekly)
- postgres_data: LVM/cloud snapshot
- media_files: rsync to remote или S3 sync

## Quarterly restore drill
1. Spin up empty Postgres container
2. gunzip + psql restore
3. Smoke-test services against it
```

## 7.3.c Alerts (Grafana + Alertmanager)

- `count_over_time({level="ERROR"}[5m]) > 10` → #oncall channel
- `rate(http_requests_total{status=~"5.."}[1m]) > 0.05` (5% error rate)
- Postgres disk usage > 80%
- Redis memory > 80%

## 7.3.d Commit

```bash
git commit -m "0.1.6: runbook + backup strategy + alert rules"
```

---

# ═══════════════════════════════════════════════════════════
# Phase 7.4 — Финальный tag
# ═══════════════════════════════════════════════════════════

## 7.4.a `docs/release-notes-v1.0.md`

```markdown
# v1.0-fastapi-production

## Migrated FROM Django TO FastAPI microservices

### Services
- user-service (8005) — auth, profile, registration, items
- hr-service (8006) — employees, departments, recruitment, time-tracking
- task-service (8007) — tasks, projects, calendar, notifications
- messenger-service (8008) — chat (Socket.IO), E2EE, attachments
- media-service (8009) — file upload/download with Range, thumbnails
- email-service (8010) — OAuth, SMTP/IMAP, DLP, crypto
- cms-service (8011) — news, contact requests, conference config
- admin-service (8012) — unified sqladmin dashboard

### Infrastructure
- PgBouncer (transaction pooling)
- Redis (Dramatiq broker + Socket.IO adapter + cache)
- Loki + Promtail + Grafana (observability)
- Let's Encrypt + nginx TLS

### Removed
- Django monolith (backend/*)
- django_migrations, django_content_type, django_admin_log, auth_permission, auth_group*, auth_user_* tables

### Rollback
- `git checkout v1.0-django-final && docker compose up -d --build`
- Restore DB from backup-pre-cutover-*.sql
```

## 7.4.b Tag + push

```bash
git tag -a v1.0-fastapi-production -m "Production release: Django → FastAPI complete"
git push origin main
git push origin v1.0-fastapi-production
```

## 7.4.c Commit

```bash
git commit -m "1.0.0: production release — FastAPI microservices"
```

---

## Что НЕ делается в этом плане

- **Отделить БД по сервисам.** Сейчас один Postgres с разными schemas. Per-service DB — потенциально следующая итерация.
- **K8s.** Docker Compose достаточно для данного масштаба.
- **Service mesh.** Линейная nginx-edge проксирование справляется.
- **Multi-region.** Единая инсталляция.
- **i18n в backend.** Пользовательские переводы — на фронте через `i18next`.

---

## Контрольный список (start-of-session)

```bash
# Git + tags
git log --oneline -5
git tag | grep django-final

# Phase 3 артефакты
ls services/{cms,media,messenger,email,admin}/app/main.py
ls services/{user,hr,task,cms,media,messenger,email}/alembic/versions/ | head -20

# Observability propagation
for svc in cms media messenger email admin; do
  test -f services/$svc/app/core/logging.py && echo "$svc: Y" || echo "$svc: N"
done

# Docker state
docker compose ps
docker compose exec db psql -U htqweb -d htqweb -c "\dn"  # schemas
docker compose exec db psql -U htqweb -d htqweb -c "SELECT table_schema, count(*) FROM information_schema.tables GROUP BY 1 ORDER BY 1;"
```

Если какая-то команда даёт неожиданный результат — зафиксировать «Desync detected» и разобраться.

---

## Лог выполненных фаз (reverse chronological)

### 2026-04-24 — 0.0.3.3 — Cut dev TLS (SFU + webtransport + certbot → production profile; Vite HTTP-only)

**Проблема.** На фронте `/` и остальной SPA работал только через HTTPS, потому что `VITE_DEV_HTTPS=true` и Vite грузил `infra/certs/{cert,key}.pem`. Единственный реальный потребитель TLS — SFU для WebRTC — сейчас не используется. 3 контейнера (`sfu`, `certbot`, `webtransport`) крутились впустую и тянули cert-ы.

**Что сделано.**
- `frontend/.env` — `VITE_DEV_HTTPS=true` → `false` (комментарий: как включить обратно при необходимости /conference).
- `docker-compose.yml` — `sfu`, `certbot`, `webtransport` переведены под `profiles: [production]` (к nginx, который был переведён в 4.5). Dev-compose теперь не поднимает ничего TLS-зависимого.
- Удалены `infra/certs/cert.pem`, `infra/certs/key.pem`. `infra/certs/generate.mjs` оставлен для восстановления при нужде.
- Остановлены и удалены запущенные `sfu`/`certbot`/`webtransport` контейнеры.

**Verification (11/11 smoke зелёные):**
| Проверка | Результат |
|---|---|
| 8 сервисов `/health/` (8005–8012) | все 200 ✓ |
| Dev-compose containers TLS-free | 28 контейнеров, 12 healthy; нет sfu/certbot/webtransport/nginx |
| HTTPS-порты наружу (443/4443/4433) | 0 экспозиций |
| login admin/admin123 | OK |
| `GET /profile/me` + `PATCH /profile/me` multipart | 200 |
| CMS публичный POST + admin stats | 201 / 200 |
| user-service pending-registrations | 200 |
| client-errors + client-events | 202 / 202 |
| HR employees list + Tasks list | 200 / 200 |
| Avatar upload end-to-end (S2S JWT) | 200 + запись в `media.audit_log` |

**Непроверено:**
- **Frontend Vite dev server** — запущен локально (host node, не docker), Claude не рестартил его. Пользователю нужно `Ctrl+C` + `npm run dev` в `frontend/`, чтобы подхватились новые `VITE_DEV_HTTPS=false` из `.env`. После этого `http://localhost:3000/` должен открываться без SSL-предупреждений.
- `/conference` страница (WebRTC) — пока не работает в dev (нужен SFU). При необходимости:
  ```
  node infra/certs/generate.mjs        # регенерируем self-signed
  echo VITE_DEV_HTTPS=true >> frontend/.env
  docker compose --profile production up -d sfu webtransport
  ```

**Отклонения от плана:** нет, изменения чисто инфраструктурные.

**Commit:** (текущий).

---

### 2026-04-24 — 0.0.3.2 — Phase 4.5 endpoint backfill + pre-deploy comprehensive logging

**Commit:** `b7c37e9` — SERVICE_JWT_SECRET S2S + change-password + avatar + client telemetry + cms audit schema fix.

**Что сделано.**

_Backfill endpoints:_
- `POST /api/users/v1/profile/change-password` — принимает new_password + опционально current_password (current_password не требуется при must_change_password=true). 200 + JSON `{detail}`. Срабатывает событие `password_changed` в structlog.
- `PATCH /api/users/v1/profile/me` переписан на `multipart/form-data`: принимает Form-поля (display_name, firstName/lastName, patronymic, bio, phone, settings=JSON) + опциональный `avatar` UploadFile. При наличии avatar — POST через httpx на `http://media-service:8009/api/media/v1/files/` с `SERVICE_JWT_SECRET` и `X-User-Id` header. Возвращает полный ProfileResponse с обновлённым `avatarUrl`.
- `POST /api/users/v1/client-errors` и `/client-events` — приём frontend-телеметрии (fatal errors + user-action audit). 202 Accepted; events идут в structlog (→ Loki).
- CMS `GET /api/cms/v1/contact-requests/stats` — уже существовал, проверен. `POST /` публичный + rate-limit 3/min — работает.
- user-service `GET /pending-registrations/` — пофиксен `TokenPayload` в dependencies (добавлены `is_staff/is_superuser/is_admin/username/email` + `model_config={"extra": "ignore"}`), 500 → 200.

_S2S infrastructure:_
- `services/user/app/services/service_tokens.py` (новый) — `issue_service_token()` выпускает короткоживущий (60s) JWT с claim `service=True`, подписанный `SERVICE_JWT_SECRET`.
- `services/media/app/auth/dependencies.py` — расширен: принимает и user JWT (по `JWT_SECRET`) и service JWT (по `SERVICE_JWT_SECRET`). При service JWT читает `X-User-Id` header для корректного `owner_id`.
- `services/media/app/api/v1/files.py` — `upload_file` правильно резолвит `owner_id` для S2S-вызовов.
- `services/media/app/schemas/file.py` — добавлен `computed_field url: str = "/api/media/v1/files/{id}"` для возврата готового download URL в upload response.
- Settings в user-service + media-service: добавлены `service_jwt_secret`, `service_jwt_algorithm`, `media_service_url`.
- docker-compose.yml: `SERVICE_JWT_SECRET` добавлен в env user-service + media-service (должны совпадать).
- `.env.example` + `.env`: добавлен `SERVICE_JWT_SECRET`.

_Backend structlog events (критические пути user-service):_
- `user_registered`, `user_approved`, `user_rejected` (registration.py)
- `token_issued`, `token_refreshed`, `admin_session_issued`, `login_failed` с reason=user_not_found|inactive|wrong_password (auth.py)
- `password_changed`, `password_change_rejected`, `profile_updated`, `profile_requested`, `avatar_upload_failed` (profile.py)
- `frontend_client_error` (error), `frontend_user_action` (info) — из client_errors.py

_Frontend telemetry:_
- `frontend/src/lib/telemetry.ts` (новый): `reportClientError()`, `logUserAction()`, `installGlobalErrorHandlers()` с keepalive fetch.
- `frontend/src/app/components/AppErrorBoundary.tsx`: `componentDidCatch` теперь вызывает `reportClientError` → backend пишет в Loki.
- `frontend/src/main.tsx`: `installGlobalErrorHandlers()` при старте приложения (ловит `window.onerror` + `unhandledrejection`).
- `frontend/src/components/LoginForm.jsx`: `logUserAction({action:"login_success"|"login_failed", meta:...})`.
- `frontend/src/lib/auth/profileStorage.ts`: `clearAuthStorage()` fire-and-forget `logUserAction({action:"logout"})` ДО очистки токена.

_Infra + DB fixes (обнаружены при smoke):_
- nginx переведён под `profiles: [production]` в docker-compose.yml — в dev не поднимается (209 unhealthy streak устранён; dev ходит через Vite proxy).
- Создана миграция `services/media/alembic/versions/002_add_audit_log.py` — `media.audit_log` отсутствовал, блокировал upload.
- Создана миграция `services/cms/alembic/versions/002_audit_log_schema.py` — `audit_log` был в public вместо cms (pgbouncer transaction-mode search_path drift).
- `services/media/app/models/audit_log.py` + `services/cms/app/models/audit_log.py`: добавлен `__table_args__ = {"schema": ...}`  для стабильности через pgbouncer.
- user-service: добавлен `python-multipart` + `email-validator` в requirements.txt.
- user-service `TokenPayload` расширен (is_staff/is_superuser/is_admin/username/email) с `extra="ignore"`.

**Verification (все зелёное):**
- 8 FastAPI сервисов `/health/` → 200 (email-service 8010 internal-only, nginx в production profile).
- `POST /profile/change-password` с wrong current → 400 ✓; с correct → 200 + login с новым паролем работает ✓.
- `PATCH /profile/me` multipart + avatar.jpg → 200 с `avatarUrl=/api/media/v1/files/{uuid}` + запись в `media.audit_log(action=file_uploaded, via_service=true)`.
- `POST /api/cms/v1/contact-requests/` анонимный → 201 + запись в `cms.audit_log(action=contact_request_submitted)`.
- `GET /api/cms/v1/contact-requests/stats` → `{unhandled: N}`.
- `GET /api/users/v1/pending-registrations/` admin → `[]` (pending реально нет).
- `POST /api/users/v1/client-errors` и `/client-events` → 202 + структурированные события в docker logs.
- structlog events видны в docker compose logs user-service (token_issued, password_changed, profile_updated, frontend_client_error, frontend_user_action).

**Непроверено / отложено:**
- Browser smoke (открытие http://localhost:3000, реальный login, avatar в DevTools Network). Dev-сервер frontend отдельно запущенным пользователем — не гоняли в этой сессии.
- Loki/Promtail/Grafana UI-проверка (сбор логов). Pending в Phase 5.4.
- Аналогичный schema-fix для audit_log в hr/task/messenger/email (может проявиться тем же симптомом при первом использовании). Вынесено в Phase 4.7.
- nginx healthcheck command (`wget` on listener) не пофиксен — nginx просто выведен из dev compose через profile.

**Отклонения от плана:**
- В плане было "единый коммит 0.0.3.2" — так и делаем (все изменения ниже единым коммитом).
- Audit для user-service — не создавали отдельную `auth.audit_log` таблицу; вместо этого все события идут в structlog (→ Loki). Долгосрочно — можно добавить.
- ProfileSidebar null-safety — уже была корректной (`data?.unhandled ?? 0`, `Array.isArray(data) ? data.length : 0`), не трогали.

---

### 2026-04-24 — 0.0.3.0 — Post-login crash fix

**Симптомы.** После login страница `/myprofile` крашилась с `TypeError: Cannot read properties of undefined (reading 'map')`.

**Root cause.**
1. [ProfileHeader.tsx:35](frontend/src/components/profile/ProfileHeader.tsx#L35) делал `profile.roles.map()`, а ответ user-service `/api/users/v1/profile/me` не содержал `roles`.
2. 13 компонентов фронта ещё шли по Django-style путям (`v1/profile/me/`, `v1/admin/users/`, `v1/contact-requests/`) → 404.

**Fix.**
- Backend: расширен `ProfileResponse` под полный `UserProfile` тип фронта (`roles, firstName/lastName, fio, avatarUrl, settings, department, position, created_at, updated_at`). `roles` derived из `is_staff`/`is_superuser`. Добавлены `PATCH /me` алиас, snake+camelCase acceptance в теле PATCH.
- Frontend: rewrite 13 путей под `users/v1/*` или `cms/v1/*`. `ProfileHeader` защищён `(profile.roles ?? []).map(...)`.

**Commit:** `1a66fed`.

---

### 2026-04-24 — 0.0.2.9 — Unify user-service API prefix + HTTP-only Vite

- Все роутеры user-service: `/api/token/`, `/api/register/`, `/api/v1/profile/` → `/api/users/v1/*`.
- Кросс-сервисный admin login (hr/task/cms/media/messenger/email/admin) → `POST /api/users/v1/token/`.
- Vite proxy упрощён: одна строка на сервис. HTTPS в Vite теперь opt-in (`VITE_DEV_HTTPS=true`).
- `frontend/Dockerfile.dev`: `npm ci` → `npm install`.
- email-service: exposed port 8010.

**Commit:** `847d8fa`.

---

### 2026-04-23 — 0.0.2.8 — Hotfix: sqladmin перекрывал SPA /admin/*

- SPA держит `/admin/users, /admin/chats, /admin/registrations` — nginx ловил весь `/admin/*` и слал в sqladmin.
- Решение: sqladmin mount → `/sqladmin/` во всех 8 сервисах. Nginx + Vite proxy обновлены. `docker-compose.dev.yml` переписан (убрана зависимость от Django backend, все Vite targets теперь FastAPI).

**Commit:** `27faf38`.

---

### 2026-04-23 — 0.0.2.7 — Phase 4: admin bootstrap + nginx cutover + compose workers + alembic init

- **Admin auth overhaul**: is_admin JWT claim, unified admin_session cookie, рабочий `login()` во всех 8 sqladmin-backend-ах, CLI-бутстрап `app.scripts.create_admin`.
- **Nginx**: убран legacy_backend (причина падения контейнера), добавлены admin_service upstream, /api/email/ location, liveness /health, IPv6-listen.
- **PgBouncer**: `IGNORE_STARTUP_PARAMETERS: search_path`, `ALTER ROLE` с покрытием всех схем.
- **Compose**: +14 worker/scheduler блоков, `healthcheck: disable: true`. Исправлен cms-scheduler (не было main()).
- **Frontend**: `socket.io-client@4.8.1`, синглтон + `useMessengerSocket` хук. Polling снижен до 30с.
- **Alembic**: `include_object + include_schemas=True` в env.py. Initial миграции для cms/media/messenger/email.
- **Cleanup**: fix_main.py, services/hr/app/routers/, services/task/app/routers/health.py.

**Commit:** `d673393`.

---

### 2026-04-23 — 0.0.2.6 — Phase 4 in-progress (frontend API clients + nginx + compose services)

См. `git show e4635e9 --stat`. 9215-строчный package-lock.json обновлён. Компоненты фронта начали ходить в новые endpoint-ы.

**Commit:** `e4635e9`.

---

### 2026-04-23 — 0.0.2.5 — Phase 3 fully completed

121 файлов, +6322/−99. `services/admin/` создан как аггрегатор. Cms/media/messenger/email полностью наполнены. Initial alembic infra. Observability propagation везде.

**Commit:** `56bb6a0`.

---

### Earlier commits (0.0.2.1–0.0.2.4)

См. git log. `2f93153` — Phase 3 bulk external session. `fc722e4` — observability + rollback tag.

---

## Desync detected (если добавится)

Формат записи:
```
### YYYY-MM-DD — Desync при старте сессии
- ожидалось: X (по таблице статусов)
- фактически: Y (по команде Z)
- причина: ...
- действие: ...
```
