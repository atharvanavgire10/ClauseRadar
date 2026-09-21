# ClauseRadar — From contract clauses to actions.

Production-quality contract obligation and risk management platform.
Deterministic business logic first; AI optional and evidence-grounded.

> **Status: Phase 00 — foundation.** Backend skeleton + frontend shell + health
> endpoint + Docker/CI scaffolding. Domain phases land incrementally on
> `phase/XX-*` branches merged into `main`.

## Quick start (local, no external services)

```bash
# 1) backend
cp .env.example .env
py -m pip install -r backend/requirements.txt
py backend/manage.py migrate
py backend/manage.py runserver   # http://localhost:8000/api/health/

# 2) frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Or with PostgreSQL + Redis:

```bash
cp .env.example .env
docker compose up --build
```

## API (Phase 00)

- `GET /api/health/` — liveness
- `GET /api/ready/` — readiness (database check)
- `GET /api/v1/` — API info

## Structure

See `docs/architecture.md` for the full plan and `docker-compose.yml` for services.

## Environment

All configuration via environment — see `.env.example`. Never commit `.env` or API keys.
AI keys (`GEMINI_API_KEY` / `OPENAI_API_KEY`) are optional; the app works without them.
