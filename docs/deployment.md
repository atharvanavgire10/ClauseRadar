# Deployment (Phase 20)

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
