# HTQWeb Platform — Microservices Migration

Enterprise internal platform (Hi-Tech Group). Currently undergoing **Strangler Fig migration** from Django monolith to microservices architecture.

## Architecture Status

```
React SPA → Nginx (API Gateway) → [Microservices | Legacy Django]
```

### Services

| Service | Status | Port | Description |
|---|---|---|---|
| **Nginx Gateway** | 🟢 Active | 80 | API Gateway, routing, rate limiting |
| **User Service** | 🟡 Dev | 8005 | Identity, JWT, auth (FastAPI) |
| **HR Service** | 🟡 Planned | — | HR management (not yet extracted) |
| **Legacy Django** | 🟢 Active | 8000 | All remaining domains (Daphne) |
| **SFU** | 🟢 Active | 4443 | Mediasoup WebRTC |
| **Redis** | 🟢 Active | 6379 | Cache |
| **PostgreSQL** | 🟢 Active | 55432 | Via PgBouncer |

See [API.md](./API.md) for full routing table and service contracts.

## Quick Start

### Docker (recommended)

```bash
docker compose up -d
```

Access:
- App: http://localhost
- Admin: http://localhost/admin/
- API docs (User Service): http://localhost:8005/docs

### Local development

#### Backend (Django)
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Frontend (React Vite)
```bash
cd frontend
npm install
npm run dev
```

#### User Service (FastAPI)
```bash
cd services/user
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8005
```

## Project Structure

```
HTQWeb1/
├── backend/              # Django monolith (legacy)
├── frontend/             # React + Vite + TypeScript
├── infra/                # Infrastructure (nginx, certs, db init)
│   ├── nginx/
│   │   └── default.conf  # API Gateway routing
│   ├── certs/            # Local TLS certs (gitignored)
│   └── db/
│       └── init-ltree.sql
├── services/             # Microservices (new)
│   ├── _template/        # Cookiecutter template
│   ├── scaffold.py       # Create new service: python scaffold.py <name> <desc>
│   ├── user/             # User/Identity Service (JWT authority)
│   └── README.md         # Services documentation
├── docker-compose.yml    # Full stack orchestration
├── API.md                # API documentation + service contracts
└── README.md             # This file
```

## Migration Progress (Strangler Fig)

| Phase | Domain | Status | Details |
|---|---|---|---|
| **Phase 0** | API Gateway | ✅ Done | Nginx routing, rate limiting, observability |
| **Phase 1a** | User/Identity | 🟡 In Progress | Service created, dual-write setup, migration script ready |
| **Phase 1b** | HR | 🔵 Planned | Models analyzed, extraction planned |
| **Phase 1c** | Audit | 🔵 Planned | Cross-service audit log |

## Key Features

*   **JWT Authentication**: SimpleJWT, stateless auth across all services
*   **API Gateway**: Nginx with path-based routing, rate limiting, health checks
*   **Strangler Fig Pattern**: Incremental migration without downtime
*   **Database per Service**: Each microservice owns its schema (via PgBouncer)
*   **Observability**: Structured logging, request ID propagation, health checks
*   **HR Management**: Departments, positions, employees, vacancies, applications, time tracking
*   **Task Tracker**: Tasks with auto-generated keys, comments, attachments, relationships
*   **Messenger**: E2EE (X25519 + AES-256-GCM), WebSocket, SFU video conferencing
*   **Internal Email**: OAuth-based sending (Gmail/Microsoft Graph), DLP scanner

## Documentation

- [API Documentation](./API.md) — Routing table, service contracts, migration strategy
- [Services README](./services/README.md) — Microservice development guide
- [User Service README](./services/user/README.md) — User/Identity Service docs

## Testing
*   Backend: `python manage.py test mainView`
*   Frontend: `npm test`

## LAN WebRTC (HTTPS + WSS)

### 1) Generate local TLS cert for IP

`mkcert` (recommended):

```powershell
mkcert -install; mkcert -cert-file .\certs\cert.pem -key-file .\certs\key.pem localhost 127.0.0.1 ::1 192.168.2.106
```

Replace `192.168.2.106` with your LAN IP.

### 2) Start SFU in secure LAN mode

Set env:

```powershell
$env:SFU_HOST="0.0.0.0"
$env:SFU_PORT="4443"
$env:SIGNALING_REQUIRE_TLS="true"
$env:TLS_CERT="D:\HTQWeb1\certs\cert.pem"
$env:TLS_KEY="D:\HTQWeb1\certs\key.pem"
```

Run:

```powershell
cd .\sfu
npm run dev
```

## Cloudflare + Bore Quick Start

Free P2P tunnel mode — no credit card, no registration required.
Full details: [docs/TUNNEL_SETUP.md](docs/TUNNEL_SETUP.md)

1. Start backend + frontend
2. Run tunnel: `.\scripts\start-sfu-tunnel.ps1`
3. Update `frontend/.env` with the signaling URL

## Architecture
Project structure and refactoring conventions are documented in:
- `docs/architecture.md`

## 🔧 WebRTC Video/Audio Troubleshooting

Если у вас проблемы с видео/аудио потоками между клиентами, начните отсюда:

### ⚡ Быстрое исправление (5 минут)
Прочитайте [QUICK_FIX.md](./QUICK_FIX.md) - пошаговое руководство по настройке

### 📖 Детальная диагностика
Прочитайте [WEBRTC_TROUBLESHOOTING.md](./WEBRTC_TROUBLESHOOTING.md) - полное руководство

### 🛠️ Инструменты диагностики

**1. Проверка конфигурации SFU:**
```bash
node scripts/check-sfu-config.js
```

**2. Диагностика в браузере:**
- Откройте консоль (F12) на странице конференции
- Вставьте содержимое [diagnose-webrtc.js](./diagnose-webrtc.js)
- Следуйте рекомендациям в выводе

### 🎯 Типичные проблемы

| Проблема | Решение |
|----------|---------|
| Видео работает только локально | Настройте `WEBRTC_ANNOUNCED_IP` в `sfu/.env` |
| Аудио есть, видео нет | Откройте порт 44444 (UDP+TCP) в firewall |
| Работает только в LAN | Настройте TURN сервер |
| Камера не работает | Нужен HTTPS (используйте ngrok/туннель) |

### 📝 Пример конфигурации

Скопируйте `sfu/.env.example` в `sfu/.env` и настройте под ваш сервер:
```bash
cp sfu/.env.example sfu/.env
```
