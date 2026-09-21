# Obligation engine (Phases 05–06)

## Model
`Obligation` links `workspace → contract → document → clause` plus denormalized
`page_number` and verbatim `source_text`. Status lifecycle:

`NEEDS_REVIEW → CONFIRMED / REJECTED → ACTIVE → IN_PROGRESS → COMPLETED`
(+ `WAIVED`). Reviewer + `reviewed_at` recorded on confirm/reject.

## Rule extraction (`obligations/extractor.py`)
Runs automatically after clause extraction for every READY document (best-effort).
A clause yields an obligation only when it contains obligation language
(`shall/must/will/agrees to/is required to/responsible for/covenants to`).
`DEFINITIONS` clauses never yield obligations (they state facts).

Normalized fields:
- `obligation_type` mapped from clause type (RENEWAL→RENEWAL_NOTICE, etc.)
- `actor` from party patterns (`The Vendor shall…`), else blank (never guessed)
- `action` = modal verb + following words (deterministic truncation)
- `frequency` from keywords (monthly/quarterly/annual/throughout the term→CONTINUOUS)
- `evidence_required` per-type map (INSURANCE→insurance certificate, …)
- `title` = actor + action; `source_text` = verbatim clause text (never invented)

## Verification workflow (`obligations/services.py`, all transactional + audited)
- `confirm_obligation` — NEEDS_REVIEW → CONFIRMED (+reviewer/reviewed_at)
- `reject_obligation` — NEEDS_REVIEW → REJECTED (+reason in audit metadata)
- `activate_obligation` — CONFIRMED → ACTIVE (operational tracking begins)
- Invalid transitions raise `ValueError` → API 400 `invalid_transition`.
- Reviewer edits title/actor via PATCH; review state preserved.
- API: `POST /api/v1/obligations/{id}/{confirm,reject,activate}/`,
  `POST /api/v1/obligations/extract/` (`{document}`), full audit history
  (`obligation.created/updated/confirmed/rejected/activated/deleted`).
