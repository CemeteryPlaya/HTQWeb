# Backend dev scripts

Diagnostic / probe scripts for the Django monolith. **Not shipped in production** — `backend/Dockerfile` deletes `scripts/dev/` during build.

Run from anywhere (each script bootstraps `sys.path` to `backend/`):

```bash
cd backend
python scripts/dev/<script>.py
```

| Script | Purpose |
|---|---|
| `debug_api.py` | Hit DRF endpoints via `APIClient` and print responses |
| `debug_db.py` | Inspect User / Employee rows directly through the ORM |
| `probe_admin.py` | Smoke `/api/v1/admin/users/` as a superuser |
| `probe_profile.py` | Smoke `/api/v1/profile/me` |
| `probe_stats.py` | Smoke task / HR statistics endpoints |
| `probe_token.py` | Exercise `SafeTokenObtainPairView` JWT issuance |
| `test_deadline.py` | Replay `Task` deadline calc against `ProductionDay` calendar |
| `verify_system.py` | Sanity-check users, profiles, and core models exist |
| `run_local.ps1` | Start `manage.py runserver` against the dockerised Postgres (port `DB_HOST_PORT`, default `55432`) |

These scripts disappear together with Django at the end of Phase 4. Anything still useful by then gets reimplemented inside the relevant `services/<X>/scripts/dev/`.
