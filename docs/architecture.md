# ClauseRadar Architecture (Phase 00)

## Product
ClauseRadar converts contracts into structured, evidence-backed operational obligations:
ingest → process → extract clauses → extract obligations → human verification →
deadlines → recurrence → risk → assignment → tracking → audit → search →
version comparison → evidence-grounded AI → notifications → public evaluation.

## Principles
1. **Deterministic core, optional AI.** Deadlines, recurrence, states, risk rules,
   permissions, audit, search, versioning, and validation never depend on an LLM.
2. **Evidence-first.** Every extracted fact links to source document/page/clause/text
   with confidence, extraction method, and review status.
3. **Same API for everyone.** The public evaluation workspace uses identical backend
   APIs and business logic as authenticated workspaces, with isolation + rate limits.

## Monorepo layout
```
ClauseRadar/
├── backend/        # Django + DRF, domain-oriented apps (grow per phase)
│   ├── config/     # settings, urls, wsgi/asgi, celery
│   └── core/       # health, pagination, error envelope, base models
├── frontend/       # React + Vite + React Router + TanStack Query
├── docs/           # architecture, database, api, engines, security, deployment
├── tests/          # cross-cutting pytest suites (health + per-phase)
├── fixtures/       # sample contracts (clearly fictional)
├── scripts/        # dev/setup helpers
├── docker/         # backend/frontend Dockerfiles, nginx conf
└── .github/        # CI
```

## Backend phases
- 01: Django core (User, Organization, Workspace, auth, permissions, audit foundation)
- 03: document ingestion (PDF/DOCX, PyMuPDF/python-docx, states)
- 04–06: clause engine → obligation engine → human verification
- 07–08: deadline engine (deterministic temporal rules) + recurrence (Celery/Redis)
- 09: deterministic explainable risk engine
- 10–11: contract operations + append-only audit
- 12: PostgreSQL full-text search
- 13: contract versioning + deterministic diff
- 14–15: optional AI provider abstraction + evidence-grounded Q&A
- 16: notifications (in-app + email abstraction, Celery)
- 17–18: public evaluation workspace + security pass
- 19–23: testing, deployment, recruiter UX, docs, final audit

## Data model (target)
User → Organization → Workspace → Contract → ContractVersion → Document →
DocumentPage → Clause → Obligation → Deadline; Evidence, RiskFinding, Task,
Comment, Notification, AuditEvent. UUIDs where appropriate, created_at/updated_at
everywhere, DB constraints + indexes on hot paths.

## Environments
- Local: SQLite + eager Celery (zero external deps) or Postgres/Redis via compose.
- Prod: PostgreSQL + Redis + Celery worker/beat, Gunicorn, WhiteNoise staticfiles.
- Frontend and API deploy independently; `VITE_API_URL` points the SPA at the API.
