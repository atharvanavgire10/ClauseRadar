# Recruiter evaluation guide

Evaluate ClauseRadar in ~10 minutes. No signup, no API key, no setup — every
action below hits the real Django API and PostgreSQL-compatible database.

## Start
1. Open the site and click **Explore ClauseRadar**. You enter the fictional
   **ACME INDUSTRIES** workspace (6 contracts, versions, 40+ obligations,
   deadlines, risk findings, audit history).

## Recommended path
1. **Vendor Master Services Agreement** — open it from Contracts.
2. **Risk Radar** — pick a high score, read why each point was added.
3. Open a finding's **source clause** (document, page, exact text).
4. **Assign** the obligation to a demo member and **start progress**.
5. **Audit Log** — your actions are already recorded, append-only.
6. **Search** “insurance” — contracts, clauses, and obligations ranked together.
7. **Versions** — compare v1 → v2 (payment 30 → 15 days, with impact + affected obligations).
8. **Ask** “What insurance obligations exist?” — open a citation to its source.
9. **Upload your own PDF** on any contract — watch processing → clauses →
   obligations arrive as NEEDS_REVIEW, then approve one yourself.
10. **Reset evaluation workspace** from the banner to restore the seed.

## What to check
- Every obligation shows its **source text, page, confidence, and method**.
- Deadlines show their **derivation rule** (never guessed dates).
- Risk findings cite **rule + points + source + affected obligation**.
- The app works identically with **no AI key configured** (see Settings → AI assistance).
- Reset restores all seed data; private workspaces are never visible to the visitor.
