# API Documentation — HTQWeb Platform

## Архитектура: API Gateway (Nginx)

Все запросы проходят через API Gateway (Nginx на порту 80).
Gateway маршрутизирует запросы к соответствующим микросервисам или legacy Django.

```
React SPA → Nginx (Gateway:80) → [Микросервисы | Legacy Django]
```

### Health Check Endpoints

| Endpoint | Описание |
|---|---|
| `GET /health` | Статус самого Gateway |
| `GET /health/ready` | Готовность upstream (legacy backend) |

### Response Headers (все ответы)

| Header | Описание |
|---|---|
| `X-Gateway` | Идентификатор шлюза (`htqweb`) |
| `X-Request-ID` | UUID для распределённой трассировки |

---

## Аутентификация

### Получить токен
*   **URL**: `/api/token/`
*   **Method**: `POST`
*   **Rate Limit**: 5 запросов/мин на IP
*   **Body**:
    ```json
    {
        "username": "your_username",
        "password": "your_password"
    }
    ```
*   **Response**:
    ```json
    {
        "access": "access_token_string",
        "refresh": "refresh_token_string"
    }
    ```

### Обновить токен
*   **URL**: `/api/token/refresh/`
*   **Method**: `POST`
*   **Rate Limit**: 5 запросов/мин на IP
*   **Body**:
    ```json
    {
        "refresh": "refresh_token_string"
    }
    ```
*   **Response**:
    ```json
    {
        "access": "new_access_token_string"
    }
    ```

---

## Маршрутизация API (Routing Table)

| Префикс | Сервис | Статус |
|---|---|---|
| `/api/token/*` | **User Service** | 🟢 Active |
| `/api/register/*` | **User Service** | 🟢 Active |
| `/api/pending-registrations/*` | **User Service** | 🟢 Active |
| `/api/v1/profile/*` | **User Service** | 🟢 Active |
| `/api/v1/admin/users/*` | **User Service** | 🟢 Active |
| `/api/hr/` | HR Service | 🟡 Legacy Django |
| `/api/tasks/` | Tasks Service | 🟡 Legacy Django |
| `/api/messenger/` | Messenger Service | 🟡 Legacy Django |
| `/api/email/` | Email Service | 🟡 Legacy Django |
| `/api/` (остальное) | Legacy Django | 🟡 Active |
| `/ws/` | WebSocket (Django Channels) | 🟢 Active |
| `/ws/sfu/` | SFU (Mediasoup) | 🟢 Active |

> 🟢 **Active** — микросервис, полностью обслуживает запросы.
> 🟡 **Legacy** — сейчас обрабатывается монолитом, будет выделен в микросервис.

---

## Контракт для новых микросервисов

При выделении домена в отдельный микросервис, он должен соответствовать следующим требованиям:

### 1. HTTP API

| Требование | Описание |
|---|---|
| **Port** | Сервис слушает на `0.0.0.0:<port>` (внутри Docker) |
| **Health Check** | `GET /health/` → `200 {"status":"ok","service":"<name>"}` |
| **Readiness** | `GET /health/ready` → `200` или `503` |
| **Request ID** | Пропускать заголовок `X-Request-ID` во все ответы |
| **Error Format** |统一的 формат ошибок: `{"error": {"code": "...", "message": "...", "details": {}}}` |

### 2. Аутентификация

| Требование | Описание |
|---|---|
| **JWT Validation** | Каждый сервис валидирует JWT самостоятельно (через `PyJWT` + secret key) |
| **User Context** | `user_id` извлекается из `payload.user_id` токена |
| **Авторизация** | Роли/permissions проверяются внутри сервиса (не на Gateway) |
| **JWT Secret** | Общий секрет через env var `JWT_SECRET` или через JWKS endpoint |

### 3. Заголовки запросов (от Gateway к сервису)

| Заголовок | Источник | Описание |
|---|---|---|
| `X-Request-ID` | Gateway | UUID для трассировки |
| `X-Real-IP` | Gateway | Реальный IP клиента |
| `X-Forwarded-For` | Gateway | Цепочка прокси |
| `X-Forwarded-Proto` | Gateway | `http` или `https` |
| `Authorization` | Клиент | Bearer JWT (пропускается как есть) |

### 4. Observability

| Требование | Описание |
|---|---|
| **Logging** | Structured JSON логирование в stdout |
| **Metrics** | `/metrics` endpoint для Prometheus (опционально) |
| **Tracing** | Поддержка OpenTelemetry (propagate `traceparent` header) |

### 5. Database

| Требование | Описание |
|---|---|
| **Isolation** | Каждый сервис использует отдельную БД или отдельную схему |
| **Connection** | Подключение через PgBouncer (`DB_HOST=pgbouncer`) |
| **Migrations** | Автозапуск migrations при старте контейнера |

### 6. Docker

| Требование | Описание |
|---|---|
| **Image** | Сборка через `docker build` или `build:` в compose |
| **Healthcheck** | Docker `HEALTHCHECK` через `/health/` |
| **Restart Policy** | `restart: unless-stopped` |

---

## Strangler Fig Migration: Как происходит миграция

1. **Все запросы идут в legacy Django** (текущее состояние)
2. **Выделяется домен** (например, HR) в отдельный сервис
3. **Новый сервис деплоится**, но запросы идут в legacy
4. **Canary release**: 10% трафика на новый сервис, 90% на legacy
5. **Мониторинг**: если ошибок нет — постепенно увеличиваем вес
6. **Полная подмена**: 100% на новом сервисе, legacy fallback убирается
7. **Legacy код удаляется** из монолита

---

## Items (Legacy)

### List Items
*   **URL**: `/api/items/`
*   **Method**: `GET`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**: List of items belonging to the user.

### Create Item
*   **URL**: `/api/items/`
*   **Method**: `POST`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Body**:
    ```json
    {
        "title": "Item Title",
        "description": "Item Description"
    }
    ```
*   **Response**: Created item object.

### Delete Item
*   **URL**: `/api/items/{id}/`
*   **Method**: `DELETE`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**: 204 No Content

---

## Rate Limiting

| Endpoint | Limit | Burst |
|---|---|---|
| `/api/token/*` | 5 req/min | 2 |
| `/api/*` (general) | 30 req/s | 20 |
| `/ws/*` | 10 req/s | 5 |

---

## Error Codes

| HTTP Status | Описание |
|---|---|
| `400` | Bad Request — неверный формат запроса |
| `401` | Unauthorized — отсутствующий/истёкший JWT |
| `403` | Forbidden — недостаточно прав |
| `404` | Not Found — ресурс не найден |
| `429` | Too Many Requests — превышен rate limit |
| `500` | Internal Server Error — ошибка сервиса |
| `502` | Bad Gateway — сервис недоступен |
| `503` | Service Unavailable — сервис не готов |
