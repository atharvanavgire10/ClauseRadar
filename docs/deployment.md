# Deployment (Phase 20; Phase 24 adds the Vercel path below)

ClauseRadar deploys as three independent units sharing PostgreSQL + Redis:
**API** (Django/Gunicorn), **worker + scheduler** (Celery worker/beat), **web**
(static Vite build served by nginx or any static host).

## Environment
All configuration is environment-only (see `.env.example`). Required in prod:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | long random secret (refused to boot on the dev default with `DEBUG=False`) |
| `DJANGO_DEBUG` | `False` in prod |
| `DJANGO_ALLOWED_HOSTS` | e.g. `api.example.com` |
| `DATABASE_URL` | e.g. `postgres://user:pass@db:5432/clauseradar` |
| `REDIS_URL` | e.g. `redis://redis:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | `False` in prod (use worker/beat) |
| `FRONTEND_URL` / `CORS_ALLOWED_ORIGINS` | SPA origin(s) |
| `MAX_UPLOAD_MB` | upload cap (default 25) |
| `EMAIL_BACKEND` | e.g. SMTP backend (see Email below) + `EMAIL_HOST/PORT/USER/PASSWORD/TLS/SSL` |
| `AI_PROVIDER`, `GEMINI_API_KEY`/`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `AI_MODEL` | optional AI |
| `PUBLIC_EVAL_ENABLED` | `True` to serve the recruiter workspace |
| `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT` | TLS hardening behind a proxy |

Never commit `.env` or keys. Frontend needs only `VITE_API_URL` at build time —
pass it explicitly (dev default is `http://localhost:8000`):

```bash
# Local dev (Vite dev server, default API origin)
cd frontend && npm run dev
# Production bundle with API-origin guard (fails on missing/unset URL,
# rejects bundles still referencing localhost:8000)
VITE_API_URL=https://api.example.com npm run build:prod
# Docker (ARG is required; build fails without it)
docker build -f docker/frontend.Dockerfile \
  --build-arg VITE_API_URL=https://api.example.com -t clauseradar-web:prod .
```

## Migrate + seed
```bash
python backend/manage.py migrate
python backend/manage.py seed_eval        # optional: recruiter workspace
python backend/manage.py collectstatic --noinput
```

## Processes
```bash
# API (3 workers)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3  # from backend/
# background work
celery -A config worker --loglevel=info   # from backend/
celery -A config beat --loglevel=info     # scheduler: recurring roll-forward + notification scan
```
`docker-compose.yml` wires db/redis/backend/worker/beat for self-hosting.

## Health + readiness
- `GET /api/health/` — liveness (no DB touch).
- `GET /api/ready/` — readiness: `{ready, checks: {database}, ai_provider}` (503 when DB down).
- Structured JSON logs to stdout; DRF envelope `{detail, code}`; no stack traces to clients.
- Media: local `MEDIA_ROOT` by default; swap `STORAGES.default` for S3 in `config/settings.py` for multi-replica prod (documented override point).

## Storage volumes (single instance)
`docker-compose.prod.yml` mounts named volumes for Postgres (`pgdata`), Redis
(`redisdata`), and uploaded media (`media` → `/app/backend/media`), so documents
and evidence survive container restarts and image rebuilds. Backup `pgdata` and
`media` on your host schedule. **Multi-replica deployments must use shared or
object storage** — local `MEDIA_ROOT` is per-instance by design.

## Email
Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` plus `EMAIL_HOST`,
`EMAIL_PORT` (default 587), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS` (default True) / `EMAIL_USE_SSL` (default False). Local dev keeps
the console backend; notification rows are always created regardless of delivery.

## OCR
The backend image does **not** ship Tesseract. Image-only/scanned PDFs report
`FAILED` with an explanatory message instead of pretending success. To enable
OCR: install the `tesseract-ocr` system package in the image and ensure the
`pytesseract` Python package is installed (already a conditional dependency on
non-Windows platforms) — no code changes needed, the extractor attempts OCR
automatically when available.

---

# Vercel-native deployment (Phase 24)

Serve the **same product** (same Django code, same React SPA, same database
schema) from a single Vercel project — no servers, no Redis, no worker:

```
Browser (SPA static, same origin)
  │  /api/* rewrites → Python serverless function (Django WSGI)
  ▼
Django ──► Neon PostgreSQL (DATABASE_URL)
  ├─► Vercel Blob, private (documents + evidence)
  └─► Vercel Cron ──► /api/internal/cron/* (Bearer CRON_SECRET)
```

The Docker + Celery stack (`docker-compose.prod.yml`) remains intact as the
fallback/self-hosted path. Nothing below changes product behavior.

## 1. Create Vercel project
Create a project from the GitHub repository (import, do not fork).

## 2. Connect GitHub repository
Connect `ClauseRadar`, production branch `main` (or a release branch).

## 3. Configure project
Set **Framework Preset to Django** in the Vercel project settings. This is
required: it activates Vercel's native Django support, which discovers
`backend/manage.py`, resolves the WSGI callable from `WSGI_APPLICATION`
(`backend/config/wsgi.py`, variable `application`), adds `backend/` to the
Python path, and runs `collectstatic` with WhiteNoise-manifest awareness.
There is no `api/index.py` adapter — native detection makes it unnecessary,
and it was removed for exactly that reason.

`vercel.json` (committed) declares the rest:
- **No `installCommand`.** A custom install command disables Vercel's Python
  dependency installation entirely, which previously deployed a function with
  no Django in it (`ModuleNotFoundError: No module named 'django'` on every
  request). Frontend deps install inside `buildCommand` instead.
- `buildCommand`: frontend `ci` + production Vite build with the API-origin
  guard (`VITE_API_URL`, defaulting to `same-origin`). No manual
  `collectstatic` step — the native Django hook runs it.
- `outputDirectory`: `frontend/dist` (SPA static files win over routes).
- `functions.backend/config/wsgi.py`: `maxDuration` 300, memory 1024 — the
  ceiling for the longest document-processing calls. Normal endpoints share
  the function (a ceiling, not a cost). Confirm the limits on the Functions
  tab after deploy. Hobby plans enforce shorter limits: large-document
  uploads may time out there; production workloads need Pro/Fluid.
- `rewrites`: explicit SPA routes → `/index.html`. There is deliberately **no**
  `/api/*` rule: API paths fall through to the Django service. If a SPA route
  is added to `frontend/src/App.tsx`, add its path here too.
- Root `requirements.txt` carries the full pinned production set (no test
  deps); `backend/requirements.txt` keeps the local/Docker set. A test pins
  the production subsets equal so they cannot drift.
- `crons` invoke the Django cron endpoints (see 7).

## 4. Configure PostgreSQL
Create a Neon project/database and copy its pooled connection string. Neon
provisions/maintains the server — nothing is added to this repository and no
credentials are committed.

## 5. Configure Vercel Blob private store
Create a Blob store in the Vercel dashboard and connect it to the project
(Vercel provisions `BLOB_READ_WRITE_TOKEN`). Use a **private** store:
Django sets `access: private` on every upload, exposes no public URLs
(`BlobStorage.url()` raises by design), and downloads stream server-side
through the permission-checked endpoints.

## 6. Configure environment variables
Set on the Vercel project (Production + Preview as appropriate):

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | long random secret (boot refuses the dev default) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `your-app.vercel.app` (comma-separated ok) |
| `DATABASE_URL` | Neon pooled connection string (**required** — no silent SQLite when `DEBUG=False`) |
| `FRONTEND_URL` | `https://your-app.vercel.app` |
| `CORS_ALLOWED_ORIGINS` | `https://your-app.vercel.app` |
| `VITE_API_URL` | `same-origin` (literal — SPA calls relative `/api/...`) |
| `VERCEL_DEPLOYMENT` | `True` (synchronous processing, no Redis) |
| `DOCUMENT_STORAGE_BACKEND` | `vercel_blob` |
| `BLOB_READ_WRITE_TOKEN` | auto-provisioned when the store is connected |
| `BLOB_API_BASE_URL` | default `https://blob.vercel-storage.com` |
| `BLOB_API_VERSION` | default `10` (bump only if Blob rejects private uploads) |
| `BLOB_PRIVATE` | `True` |
| `PUBLIC_EVAL_ENABLED` | `True` (recruiter workspace; same throttles/caps, no Celery needed) |
| `PUBLIC_EVAL_SLUG` | `eval` |
| `MAX_UPLOAD_MB` | `4` — Vercel request-body limits (~4.5 MB) cap proxied uploads; larger files need a direct-to-Blob flow (not implemented) |
| `CRON_SECRET` | long random string (see 7) |
| `EMAIL_BACKEND` + `EMAIL_HOST/PORT/USER/PASSWORD/TLS/SSL`, `DEFAULT_FROM_EMAIL` | SMTP for notifications (console default = no delivery) |
| `AI_PROVIDER`, `GEMINI_API_KEY`/`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `AI_MODEL` | optional; deterministic system works with `none` |

## 7. Configure CRON_SECRET
Generate a long random value, set `CRON_SECRET` on the project. Vercel Cron
automatically sends it as `Authorization: Bearer <CRON_SECRET>`; the endpoints
compare in constant time and reject everything else (403, also when unset).
`vercel.json` already schedules:
- `0 2 * * *` → `/api/internal/cron/recurring-deadlines/`
- `30 2 * * *` → `/api/internal/cron/deadline-scan/`
Both call the existing services directly (no Beat/worker) and are idempotent
(update_or_create generation, per-day notification dedupe) with audit entries
(`cron.recurring_generated`, `cron.deadline_scan`).

## 8. Deploy
Push to the production branch or press Deploy. The build installs frontend
deps, builds the SPA, installs Python deps, and collects static files.

## 9. Run migrations
Vercel has no pre-deploy hook and migrations never run per-request. Run once
from any machine with the pinned dependencies and the **production**
`DATABASE_URL` (deterministic, normal Django migrations):
```bash
DATABASE_URL='postgres://...' python backend/manage.py migrate
```

## 10. Seed evaluation workspace
```bash
DATABASE_URL='postgres://...' python backend/manage.py seed_eval
```
Run it with the **same storage backend as runtime** (`DOCUMENT_STORAGE_BACKEND=vercel_blob`
plus `BLOB_READ_WRITE_TOKEN`) so seed files land in Blob; rows seeded against local
disk would reference files the Vercel function cannot see.

## 11. Verify health endpoint
```bash
curl -fs https://your-app.vercel.app/api/health/
curl -fs https://your-app.vercel.app/api/ready/
```

## 12. Verify public evaluation
Open `/welcome` → Explore ClauseRadar (no login): seeded contracts, clauses,
obligations, evidence, and risk must render from the API.

## 13. Verify upload
Upload a PDF on any eval contract: expect `READY` with extracted pages
(synchronous on Vercel; the response reflects the final stored state).

## 14. Verify document processing
Confirm clauses, obligations (`NEEDS_REVIEW`), and an audit trail appear for
the uploaded document; approve one obligation.

## 15. Verify cron
Trigger each cron path manually once with the secret and check counts + audit:
```bash
curl -fs -X POST https://your-app.vercel.app/api/internal/cron/recurring-deadlines/ \
  -H "Authorization: Bearer $CRON_SECRET"
curl -fs -X POST https://your-app.vercel.app/api/internal/cron/deadline-scan/ \
  -H "Authorization: Bearer $CRON_SECRET"
```
Unauthenticated calls must return 403.

## 16. Verify private document download
As the visitor, `GET /documents/{id}/download/` returns bytes; anonymous and
cross-workspace requests return 401/404 — never Blob bytes or a public URL.
Blob URLs never appear in API responses (the `file` field is an opaque
identifier); there is no public read path by design.

## Vercel local-build check
`vercel build` requires an authenticated, linked project and cannot run in CI
here; the equivalent verified gates are: `npm run build:prod` (both API modes),
`manage.py check`, the `tests/test_vercel.py` suite (18 tests, incl. a fake
Blob server and cron auth), and `vercel.json` structural tests. Live Blob,
Cron, and Neon behavior must be verified once with real credentials using the
checklist above — this repository does not claim otherwise.
