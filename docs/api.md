# ClauseRadar API (v1)

Base: `/api/v1/` — JSON only, paginated envelope `{count, next, previous, results}`.
Errors: `{detail, code, errors?}`. Auth: session cookie or `Authorization: Token <key>`.

## Auth — `/api/v1/auth/`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `register/` | no | `{email, password, display_name?}` → `{user, token}` (201) |
| POST | `login/` | no | `{email, password}` → `{user, token}` (200) |
| POST | `logout/` | yes | revokes token, ends session |
| GET | `me/` | yes | current user |

## Organizations — `/api/v1/organizations/`
Standard ModelViewSet scoped to caller's memberships. `POST` creates org + OWNER
membership and writes `organization.created` audit event.

## Workspaces — `/api/v1/workspaces/`
Scoped to caller's memberships. Fields: `organization, name, slug, workspace_type,
description, role`. Extra: `GET /{id}/members/`, `POST /{id}/add-member/`
`{email, role}` (writer roles only). Creation writes `workspace.created`.

## Contracts — `/api/v1/contracts/`
Tenant-scoped by workspace membership; filter `?workspace=<uuid>&status=&counterparty=`,
search `title, counterparty, description`. Validation: `end_date >= start_date`.
Writes `contract.created / contract.updated / contract.deleted` audit events.
VIEWER role is read-only.

## Audit — `/api/v1/audit/`
Read-only (`GET` list/detail). Filters: `?workspace=&organization=&entity_type=&action=`.
Append-only: POST/PUT/PATCH/DELETE return 405. Admin UI likewise disables add/delete.

## Health
`GET /api/health/` liveness, `GET /api/ready/` readiness (DB check + ai_provider).
