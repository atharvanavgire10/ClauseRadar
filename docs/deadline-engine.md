# Deadline engine (Phase 07)

Pure-Python deterministic temporal rules in `deadlines/engine.py` — no I/O, no
LLM, fully unit-tested including timezones and edge dates.

## Functions
- `shift(day, n, direction=before|after, business=False)` — calendar or
  business-day shifting (business days skip Sat/Sun). Example: renewal
  15 Dec 2026, 60 days before → 16 Oct 2026.
- `add_business_days(day, n)` — signed business-day arithmetic.
- `parse_explicit_date(text)` — ISO (`2026-12-15`) and long (`15 Dec 2026`)
  dates; returns `None` when absent (callers skip — dates are never invented).
- `parse_relative(text)` — `within 30 days`, `60 days before/after`.
- `deadline_status(due, today, completed, waived)` — UPCOMING / DUE_SOON
  (≤7 days) / OVERDUE / COMPLETED / WAIVED.
- `renewal_notice_date(renewal, notice_days)` and `ensure_aware`/`today_in_tz`.

## Generation (`deadlines/services.py`)
- `generate_for_contract` — RENEWAL + RENEWAL_NOTICE (default 30 days before,
  or the notice period stated in the contract's own obligations) + EXPIRY.
  Contracts without dates yield zero deadlines.
- `generate_for_obligation` — FIXED deadlines only from explicit dates in
  source text.
- `update_or_create` on (workspace, contract, obligation, title, kind) makes
  generation idempotent; runs automatically on contract create/update and after
  obligation extraction (best-effort, never fatal).

## API
Statuses are **derived at read time** (never stored, never stale).
`GET /api/v1/deadlines/?status=OVERDUE|DUE_SOON|...`,
`POST /{id}/{complete,reopen,waive}/`, `POST /generate/` (`{contract}`).
All transitions audited (`deadline.completed/reopened/waived`,
`contract.deadlines_generated`).
