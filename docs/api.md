# ClauseRadar API (v1) — complete reference

Base: `/api/v1/` — JSON only, paginated envelope `{count, next, previous, results}`.
Errors: `{detail, code, errors?}`. Auth: session cookie or `Authorization: Token <key>`.
Every list endpoint is tenant-scoped to the caller's workspace memberships.

## Auth — `/api/v1/auth/`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `register/` | no | `{email, password, display_name?}` → `{user, token}` (201) |
| POST | `login/` | no | `{email, password}` → `{user, token}` (200) |
| POST | `logout/` | yes | revokes token, ends session |
| GET | `me/` | yes | current user |

## Tenancy — organizations & workspaces
Standard scoped ModelViewSets. `POST /organizations/` creates org + OWNER membership
(`organization.created`). `POST /workspaces/` creates workspace + OWNER membership
(`workspace.created`). Extras: `GET /workspaces/{id}/members/`,
`POST /workspaces/{id}/add-member/` `{email, role}` (writers only).

## Contracts — `/api/v1/contracts/`
Tenant-scoped CRUD; filter `?workspace=&status=&counterparty=`, search title/counterparty/
description. Validation: `end_date >= start_date`. Writes `contract.created/updated/deleted`.
- `GET /contracts/{id}/versions/` — version list (auto-created per uploaded document).
- `GET /contracts/{id}/compare/?from=1&to=2` — deterministic diff
  `{added, removed, modified[{old, new, similarity, impact, affected_obligations}], unchanged, counts}`.

## Documents — `/api/v1/documents/`
`POST` multipart (`contract`, `file` PDF/DOCX): magic-byte validation, 25 MB cap,
SHA-256 duplicate detection (409 + `existing_id`), eager-or-Celery processing
(UPLOADED→PROCESSING→READY|FAILED). Eval workspaces capped at 30 docs (429).
- `GET /documents/{id}/pages/` — extracted page texts.
- `POST /documents/{id}/reprocess/` — idempotent retry.
- `GET /documents/{id}/download/` — authenticated file response.

## Clauses — `/api/v1/clauses/`
Read-only list/detail (filter `workspace/contract/document/clause_type/page_number`,
search heading/text) + `POST /clauses/extract/` `{document}` (idempotent rebuild).
Each row carries document, page, offsets, confidence, method (RULE/LLM/HYBRID).

## Obligations — `/api/v1/obligations/`
Filter `workspace/contract/status/obligation_type/frequency/owner/priority`, full search.
`POST` creates manual NEEDS_REVIEW items; `PATCH` edits; lifecycle actions:
`POST /obligations/{id}/{confirm,reject,activate,start,complete,reopen,waive}/`,
`POST /obligations/{id}/assign/` `{email}` (workspace member only),
`POST /obligations/extract/` `{document}`.

## Deadlines — `/api/v1/deadlines/`
Statuses derived at read time. Filter `?status=OVERDUE|DUE_SOON|UPCOMING|COMPLETED|WAIVED`.
`POST /deadlines/{id}/{complete,reopen,waive}/`, `POST /deadlines/generate/` `{contract}`,
`POST /deadlines/generate-recurring/` `{obligation}`.

## Risks — `/api/v1/risks/`
Read-only findings + `GET /risks/summary/?contract=` `{score, level, findings}` +
`POST /risks/assess/` `{contract}` (idempotent regenerate).

## Operations — comments / evidence / tasks
- `/api/v1/comments/` CRUD (author-only edits; must target contract or obligation).
- `/api/v1/evidence/` upload (PDF/DOCX/PNG/JPG, magic-checked) + list + download + delete.
- `/api/v1/tasks/` CRUD with assignee/status/due date.

## Search — `/api/v1/search/`
`?q=&types=contract,document,clause,obligation,evidence&workspace=&contract=`
`&obligation_type=&risk_min=&date_from=&date_to=&limit=` → ranked
`{query, count, counts, results[{type, id, title, subtitle, snippet, rank}]}`.
PostgreSQL full-text when available, ORM fallback otherwise.

## AI — `/api/v1/ai/`
- `GET /ai/status/` → `{provider, configured, model, note}`.
- `POST /ai/classify/` `{text}` → `{rule, ai, used}` (AI validated, rules fallback).
- `POST /ai/ask/` `{workspace|contract, question}` → `{answer, citations[{document_id, document_name, page_number, clause_id, obligation_id, contract_id, source_text}], intent}`; insufficient evidence stated explicitly.

## Notifications — `/api/v1/notifications/` + `/api/v1/notification-prefs/`
Own notifications only: list, `POST /{id}/read/`, `POST /read-all/`,
`GET /unread-count/`; prefs `GET /all/` + `PATCH /{id}/` (in_app/email enforced server-side).

## Evaluation — `/api/v1/eval/` (no auth, throttled)
`GET /info/` (seed stats), `POST /session/` (visitor token, 30/hour),
`POST /reset/` (reseed, 10/hour). Visitor uses all endpoints above via standard
tenant scoping — same APIs, same business logic.

## Audit — `/api/v1/audit/`
Read-only. Filters `workspace/organization/entity_type/entity_id/action`, search.
POST/PUT/PATCH/DELETE → 405; rows ORM-immutable.

## Health
`GET /api/health/` liveness, `GET /api/ready/` readiness (`{ready, checks, ai_provider}`).
