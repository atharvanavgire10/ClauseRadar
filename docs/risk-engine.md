# Risk engine (Phase 09)

Deterministic, explainable scoring in `risks/rules.py`. No ML, no randomness:
score = sum of triggered rule weights, capped at 100.

## Rules (weights configurable via `RISK_WEIGHTS` setting)
| Rule | Default | Trigger |
|---|---|---|
| `deadline_overdue` | +30 | open obligation has an overdue, uncompleted deadline |
| `evidence_missing` | +20 | `evidence_required` set while status is CONFIRMED/ACTIVE/IN_PROGRESS |
| `liability_exposure` | +25 | source clause is LIABILITY/INDEMNIFICATION |
| `no_owner` | +7 | open obligation with no owner |
| `renewal_approaching` | +15 | renewal within 60 days (contract-level) |
| `review_backlog` | +10 | NEEDS_REVIEW for ≥14 days |

Levels: 0–29 LOW, 30–59 MEDIUM, 60–79 HIGH, 80–100 CRITICAL.

## Findings
`RiskFinding` rows persist per assessment with rule, points, severity, title,
explanation, JSON evidence (deadline/clause/source refs), and affected
obligation. `assess_contract_risks` deletes + rebuilds per contract in one
transaction (idempotent, audited as `contract.risk_assessed`).

## API
`GET /api/v1/risks/` (filters), `GET /api/v1/risks/summary/?contract=`,
`POST /api/v1/risks/assess/` (`{contract}`). Read-only list; no manual score
editing — scores are always recomputed from evidence.
