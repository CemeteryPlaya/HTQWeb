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

## Cloudflare + Bore Quick Start (Recommended)

Free P2P tunnel mode — no credit card, no registration required.  
Uses **Cloudflare Quick Tunnels** for signaling (HTTPS/WSS) and **Bore** for raw TCP media traffic.  
Full details: [docs/TUNNEL_SETUP.md](docs/TUNNEL_SETUP.md)

1. Start backend:
```powershell
cd .\backend
python manage.py runserver 0.0.0.0:8000
```

2. Start frontend:
```powershell
cd .\frontend
npm run dev
```

3. Start SFU + tunnels (single orchestrator script):
```powershell
.\scripts\start-sfu-tunnel.ps1
```

The script auto-downloads `cloudflared.exe` and `bore.exe` to `tools/`, starts both tunnels,
prints the public URLs and starts Mediasoup SFU.

4. Copy the signaling URL from the console output and update `frontend/.env`:
```env
VITE_SFU_URL=wss://xxxx.trycloudflare.com/ws/sfu
```

5. Open `https://xxxx.trycloudflare.com` and join the conference.
Do not hardcode `VITE_SFU_URL`; keep it empty when testing on LAN.
If Vite prints HMR websocket errors through tunnel, set `VITE_DISABLE_HMR=true` in `frontend/.env`.

## InstaTunnel + Local Nginx Reverse Proxy (Legacy)

For dynamic InstaTunnel domains with unified routing on a single port:

- Nginx config template: `nginx/instatunnel-local-8080.conf`
- Full setup guide (Ubuntu commands + JS example): `docs/instatunnel-nginx-local.md`

## Architecture
Project structure and refactoring conventions are documented in:
- `docs/architecture.md`
