# React + Django Integration Project

This project integrates a React frontend with a Django backend using REST API (Django REST Framework) and JWT authentication.

## Setup

### Backend
1.  Navigate to `backend`: `cd backend`
2.  Install dependencies: `pip install django djangorestframework djangorestframework-simplejwt django-cors-headers`
3.  Migrate database: `python manage.py migrate`
4.  Run server: `python manage.py runserver`

### Frontend
1.  Navigate to `frontend`: `cd frontend`
2.  Install dependencies: `npm install`
3.  Run dev server: `npm run dev`

## Features

*   **User Profile**: `/myprofile` page with avatar upload, display name, and bio editing. Protected by Auth Guard.
*   **JWT Authentication**: Secure login/access using SimpleJWT.
*   **Items API**: Create and list items protected by authentication.
*   **React Integration**: Axios client with interceptors for token management.

## Configuration

### Frontend
Create `.env` file in `frontend` directory based on `.env.example`:
```
VITE_API_BASE_URL="http://localhost:8000/api/"
```

## Testing
*   Backend: `python manage.py test mainView`
*   Frontend: `npm test`

## LAN WebRTC (HTTPS + WSS)

### 1) Generate local TLS cert for IP

`mkcert` (recommended):

```powershell
mkcert -install; mkcert -cert-file .\certs\cert.pem -key-file .\certs\key.pem localhost 127.0.0.1 ::1 192.168.2.106
```

`openssl` (fallback):

```powershell
openssl req -x509 -nodes -newkey rsa:2048 -keyout .\certs\key.pem -out .\certs\cert.pem -days 365 -subj "/CN=192.168.2.106" -addext "subjectAltName=IP:192.168.2.106,DNS:localhost,IP:127.0.0.1"
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

### 3) Start frontend over HTTPS

`vite.config.ts` auto-loads `certs/cert.pem` + `certs/key.pem` and serves `https://<LAN-IP>:3000`.

## Ngrok Quick Start (Recommended)

Use ngrok as HTTPS edge and keep all app traffic on one origin (`:3000`).
Vite proxy will route:
- `/api/*` -> backend (`127.0.0.1:8000`)
- `/ws/sfu/*` -> SFU (`127.0.0.1:4443`)

1. Start backend:
```powershell
cd .\backend
python manage.py runserver 0.0.0.0:8000
```

2. Start SFU:
```powershell
cd .\sfu
$env:SFU_HOST="0.0.0.0"
$env:SFU_PORT="4443"
npm run dev
```

3. Start frontend:
```powershell
cd .\frontend
npm run dev
```

4. Start ngrok tunnel to frontend only:
```powershell
ngrok http 3000
```

5. Open `https://<your-ngrok-domain>.ngrok-free.app` and join conference.
Do not hardcode `VITE_SFU_URL`; keep it empty so signaling stays same-origin.
If Vite prints HMR websocket errors through tunnel, set `VITE_DISABLE_HMR=true` in `frontend/.env`.

## Ngrok TCP-Only SFU Media (Mediasoup)

Use this flow when SFU is behind NAT and media must go through `ngrok tcp`.

1. Start ngrok TCP tunnel for the SFU media port (`44444`):
```powershell
cd .\sfu
ngrok tcp 44444
# or:
ngrok start sfu-media --config .\ngrok.tcp.yml
```

2. Start SFU through the ngrok wrapper:
```powershell
cd .\sfu
npm run start:ngrok-tcp
```

The wrapper waits for `http://127.0.0.1:4040/api/tunnels`, resolves
`tcp://<host>:<port>`, forces TCP-only env, and injects:
- `NGROK_PUBLIC_IP`
- `NGROK_PUBLIC_PORT`
- `WEBRTC_EXPOSE_INTERNAL_IP=false`

At signaling time the server rewrites transport ICE candidates to a single TCP
candidate with ngrok external `IP:port`, so local `192.168.x.x`/mDNS candidates
are not sent to clients.

LiveKit reference config for the same TCP-only intent:
- `docs/livekit.tcp-only.ngrok.reference.yml`
- Full step-by-step guide: `docs/ngrok-tcp-mediasoup.md`

## InstaTunnel + Local Nginx Reverse Proxy (Legacy)

For dynamic InstaTunnel domains with unified routing on a single port:

- Nginx config template: `nginx/instatunnel-local-8080.conf`
- Full setup guide (Ubuntu commands + JS example): `docs/instatunnel-nginx-local.md`

## Architecture
Project structure and refactoring conventions are documented in:
- `docs/architecture.md`
