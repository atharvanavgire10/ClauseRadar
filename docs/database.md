# ClauseRadar Database (Phase 01)

## Tenancy model
`User` (custom, `accounts_user`, email login) → `OrganizationMembership` →
`Organization` → `Workspace` (`organization` FK, `organization+slug` unique) →
`WorkspaceMembership` → domain objects (`Contract.workspace` FK, …).

Every list queryset filters by `workspace__memberships__user = request.user`
(superusers bypass for admin). Object writes re-check via
`core.permissions.user_can_{access,write}_workspace`. Cross-workspace access
returns 404 (list filtering) or 403/404 on direct access — never data leakage.

## Tables (Phase 01)
- `accounts_user` — UUID PK, unique email, display_name, created/updated_at.
- `organizations_organization` — UUID PK, name, unique slug, created_by, timestamps.
- `organizations_organizationmembership` — unique (organization, user), role OWNER/ADMIN/MEMBER.
- `workspaces_workspace` — UUID PK, organization FK, slug unique-per-org, type
  STANDARD/PUBLIC_EVAL, public_slug unique nullable, description, created_by, timestamps.
- `workspaces_workspacemembership` — unique (workspace, user), role OWNER/ADMIN/MEMBER/VIEWER.
- `contracts_contract` — UUID PK, workspace FK, title/counterparty/status/dates,
  indexes on (workspace, status) and (workspace, -created_at).
- `audit_auditevent` — UUID PK, actor/org/workspace nullable FKs, entity_type,
  entity_id, action, metadata JSONB (json on sqlite), created_at; indexes on
  (workspace, -created_at), (entity_type, entity_id), (workspace, action).

## Conventions
- UUID PKs on domain models; `created_at` indexed for ordering; `updated_at` everywhere.
- All timestamps timezone-aware (`USE_TZ`, UTC).
- State changes that must stay consistent use `transaction.atomic` + `audit.services.log_event`.
- Future phases add documents/clauses/obligations/deadlines/risks/tasks/comments/
  notifications referencing `Workspace` and `Contract` — no breaking changes to Phase 01 tables.
