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
| `EMAIL_BACKEND` | e.g. SMTP backend + host/user/password vars |
| `AI_PROVIDER`, `GEMINI_API_KEY`/`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `AI_MODEL` | optional AI |
| `PUBLIC_EVAL_ENABLED` | `True` to serve the recruiter workspace |
| `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT` | TLS hardening behind a proxy |

Never commit `.env` or keys. Frontend needs only `VITE_API_URL` at build time.

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
