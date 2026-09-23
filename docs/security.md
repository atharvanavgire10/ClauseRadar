# Security (Phase 18)

## Tenant isolation
Every domain queryset is scoped to `workspace__memberships__user = request.user`
(superusers excepted for admin). Direct-object access returns 404 outside the
tenant; write paths re-check via `core.permissions.user_can_{access,write}_workspace`
(VIEWER is read-only). Covered by `tests/test_security.py` probing **every**
endpoint for cross-workspace reads, writes, and list leakage.

## Authentication & sessions
- Email + password with minimum-length validation; token (`Authorization: Token`)
  and session auth. Logout revokes tokens.
- `SessionAuthentication` enforces CSRF for cookie-based clients; token clients
  are CSRF-exempt by design (no cookies). When both credentials are present
  (SPA sends the stored token plus same-origin cookies), the token identity
  wins — otherwise a logged-in browser exploring the public evaluation
  workspace would silently operate as the wrong user.
- The CSRF cookie is readable by the SPA (`CSRF_COOKIE_HTTPONLY=False` always);
  the frontend reads `csrftoken` from `document.cookie` and sends it as
  `X-CSRFToken` on unsafe methods. A public GET (`/api/v1/eval/info/`) primes
  the cookie first so the session bootstrap POST already has a token. If a
  future config ever sets `CSRF_COOKIE_HTTPONLY=True`, Django refuses to start.
- Public evaluation uses a locked-down visitor user (unusable password) with
  membership in ONLY the eval workspace, plus per-IP throttles
  (`eval_session` 30/hour, `eval_reset` 10/hour) and an eval upload cap (30 docs).

## Files
- Magic-byte validation (never trust extensions/MIME), size caps, filename
  sanitization; uploads never executed; downloads require workspace access
  (401/403 otherwise). Eval uploads additionally capped.

## Transport & headers
- `core.middleware.SecurityHeadersMiddleware`: `X-Content-Type-Options: nosniff`,
  `Referrer-Policy`, `Permissions-Policy`; clickjacking middleware enabled.
- CORS allowlist from `CORS_ALLOWED_ORIGINS`; credentials enabled for the SPA.

## Secrets & errors
- All config via environment (`.env.example` documents everything); `.env`
  gitignored and never committed; production refuses the dev `SECRET_KEY`
  with `DEBUG=False`.
- Consistent `{detail, code}` error envelope; stack traces never serialized.

## Audit integrity
`AuditEvent` rows are ORM-immutable (updates/deletes raise) and the API is
read-only (PUT/PATCH/POST/DELETE → 405); admin disables add/delete.
