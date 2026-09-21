# ClauseRadar — From contract clauses to actions.

Production-quality contract obligation and risk management platform.
Deterministic business logic first; AI optional and evidence-grounded.

## 1. Product overview
ClauseRadar converts contracts into structured, evidence-backed operational
obligations: ingest → process → extract clauses → extract obligations → human
verification → deadlines → recurrence → risk → assignment → tracking → audit →
search → version comparison → evidence-grounded Q&A → notifications, plus a
public evaluation workspace a recruiter can use with no signup.

## 2. Problem
Contract duties hide in PDFs: renewals are missed, insurance lapses, notice
periods expire, and nobody can prove who knew what. AI-only tools hallucinate
clauses, invent dates, and leave no audit trail.

## 3. Solution
Deterministic engines for everything verifiable (extraction rules, deadline
math, recurrence, risk weights, diffs, permissions, audit) with AI strictly as
an optional, validated enhancement. Every fact links to its source document,
page, clause, and exact text with confidence, method, and review status.

## 4. Features
- PDF/DOCX ingestion with page segmentation, duplicate detection, OCR attempt
- 16-category deterministic clause detection with source navigation
- Structured obligation extraction (actor/action/requirement/frequency/evidence)
- Approve / reject / edit / activate / start / complete / reopen / waive / assign
- Timezone-aware deadline engine + business days + recurring roll-forward
- Explainable risk scoring (every point cites rule + source + obligation)
- Owner assignment, priority, notes, comments, evidence attachments, tasks
- Append-only audit trail (ORM-immutable, read-only API)
- Unified ranked search (Postgres full-text, ORM fallback)
- Contract versions with ADDED/REMOVED/MODIFIED/UNCHANGED diffs + impact notes
- Optional Gemini/OpenAI-compatible AI (validated, never fatal, RULE fallback)
- Evidence-grounded Q&A with clickable citations and honest "insufficient evidence"
- In-app + email notifications with preferences, dedupe, Celery beat scans
- Public evaluation workspace: seed, explore, mutate, upload, reset — no signup

## 5. Screenshots
Run the app and open `/welcome` → Explore ClauseRadar (seeded ACME workspace).
Screenshots placeholder: landing, contract detail with evidence, Risk Radar,
version comparison, Ask with citations. (Docs describe each flow; E2E in
`frontend/e2e/recruiter.spec.ts` pins the journey.)

## 6. Architecture
See [docs/architecture.md](docs/architecture.md). Monorepo: `backend/` (Django +
DRF apps per domain), `frontend/` (React + Vite + Router + TanStack Query),
`docs/`, `tests/` (pytest), `fixtures/`, `scripts/`, `docker/`, `.github/` (CI
with backend, frontend, and Playwright E2E jobs).

## 7. Data model
See [docs/database.md](docs/database.md). Tenancy: User → Organization →
Workspace (memberships) → Contract → ContractVersion → Document → DocumentPage
→ Clause → Obligation → Deadline; Evidence, RiskFinding, Task, Comment,
Notification(+Preference), AuditEvent. UUIDs, timestamps, constraints, indexes.

## 8. Document pipeline
See [docs/extraction.md](docs/extraction.md). Magic-byte validation, size caps,
SHA-256 dedupe, PyMuPDF/python-docx extraction, OCR attempt, Celery-or-eager
processing, idempotent reprocess, authenticated download.

## 9. Obligation engine
See [docs/obligation-engine.md](docs/obligation-engine.md). Rule-based,
evidence-bound, NEEDS_REVIEW-first with confirm/reject/activate/start/complete/
reopen/waive/assign transitions, all transactional and audited.

## 10. Deadline engine
See [docs/deadline-engine.md](docs/deadline-engine.md). Pure-function temporal
rules (spec example: renewal 15 Dec 2026 − 60 days = 16 Oct 2026), derived
statuses, idempotent generation, recurring roll-forward with beat schedule.

## 11. Risk engine
See [docs/risk-engine.md](docs/risk-engine.md). Weighted explainable rules
(spec example composes 30+20+25+7 = 82), levels, persisted findings, summary +
assess endpoints.

## 12. Evidence model
Source document + page + clause + verbatim text + confidence + method
(RULE/LLM/HYBRID) + reviewer/reviewed_at on every obligation; Q&A citations
carry document/page/clause/source; audit history per obligation in the UI.

## 13. AI architecture
See [docs/ai.md](docs/ai.md). Provider abstraction, env-only keys, validated
outputs, graceful degradation. Deterministic retrieval Q&A (templates over
retrieved rows) so answers cannot hallucinate.

## 14. Security
See [docs/security.md](docs/security.md). Tenant isolation tests on every
endpoint, locked-down eval visitor, magic-byte uploads, throttles, security
headers, secret guards, safe error envelope, immutable audit.

## 15. API documentation
See [docs/api.md](docs/api.md) for the complete `/api/v1/` reference.

## 16. Testing
- Backend: `py -m pytest -q` (120+ tests: units, API, integration, security).
- Frontend: `npm --prefix frontend run test` (vitest), `run typecheck`, `run build`.
- E2E: `npm --prefix frontend run test:e2e` (Playwright recruiter journey, live servers).
- CI runs all three. Never weaken assertions to pass; failing tests stop the phase.

## 17. Deployment
See [docs/deployment.md](docs/deployment.md). Gunicorn API, Celery worker/beat,
Postgres/Redis via compose, WhiteNoise staticfiles, `/api/health` + `/api/ready`,
env-only config, TLS via proxy.

## 18. Local setup
```bash
cp .env.example .env
py -m pip install -r backend/requirements.txt
py backend/manage.py migrate
py backend/manage.py seed_eval        # optional demo data
py backend/manage.py runserver        # http://127.0.0.1:8000/api/health/
cd frontend && npm install && npm run dev   # http://localhost:5173
```
Or `docker compose up --build` (Postgres + Redis + API + worker + beat).

## 19. Environment variables
See [.env.example](.env.example) (Django, DB, Redis/Celery, CORS, uploads, eval,
AI, email, pagination) and `frontend/.env.example` (`VITE_API_URL`).

## 20. Recruiter evaluation guide
See [docs/recruiter-guide.md](docs/recruiter-guide.md). One click (**Explore
ClauseRadar**) → seeded ACME workspace → inspect, mutate, upload, reset.

## 21. Known limitations
- OCR needs a Tesseract binary; scanned PDFs without it report FAILED honestly.
- DOCX has no native pages (chunked pseudo-pages).
- Search ranking on SQLite is heuristic; Postgres enables full-text rank.
- Single shared eval workspace (reset anytime); no per-visitor sandboxing.
- Email delivery needs a configured backend (console by default).

## 22. Future roadmap
Per-visitor eval sandboxes, S3 media backend, Postgres trigram search, clause-level
version alignment UI, SLA breach prediction, SSO/SCIM, mobile app, multi-language
extraction.
