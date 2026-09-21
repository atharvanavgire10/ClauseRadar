"""Deterministic, explainable risk rules. Weights configurable via settings.RISK_WEIGHTS.

Every rule returns findings as plain dicts: rule, points, severity, title,
explanation, obligation (or None), evidence (source refs). Scoring is a pure
sum capped at 100 — no randomness, every point cites its rule and source.
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings

from deadlines.engine import today_in_tz

DEFAULT_WEIGHTS = {
    "deadline_overdue": 30,
    "evidence_missing": 20,
    "liability_exposure": 25,
    "no_owner": 7,
    "renewal_approaching": 15,
    "review_backlog": 10,
}

REVIEW_BACKLOG_DAYS = 14
RENEWAL_WINDOW_DAYS = 60


def weights() -> dict:
    configured = getattr(settings, "RISK_WEIGHTS", None) or {}
    return {**DEFAULT_WEIGHTS, **configured}


def level_for(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def assess_obligation(ob, *, today=None) -> list[dict]:
    """Rule findings for one obligation. Pure reads — no DB writes."""
    today = today or today_in_tz()
    w = weights()
    findings: list[dict] = []
    active = ob.status in ("CONFIRMED", "ACTIVE", "IN_PROGRESS")

    overdue = [d for d in ob.deadlines.all() if d.due_date < today and not d.completed and not d.waived]
    if overdue and ob.status not in ("COMPLETED", "WAIVED", "REJECTED"):
        worst = min(overdue, key=lambda d: d.due_date)
        findings.append({
            "rule": "deadline_overdue", "points": w["deadline_overdue"], "severity": "HIGH",
            "title": f"Overdue deadline: {worst.title}",
            "explanation": (
                f"Deadline '{worst.title}' was due {worst.due_date} "
                f"({(today - worst.due_date).days} days ago) and is not completed. {worst.rule}"
            ),
            "obligation": ob,
            "evidence": {"deadline_id": str(worst.id), "due_date": str(worst.due_date),
                         "source_text": (ob.source_text or "")[:500], "page_number": ob.page_number},
        })

    # Evidence attachments (Phase 10) satisfy the requirement; otherwise an open
    # obligation with declared evidence_required is missing it.
    has_evidence = ob.evidences.count() if hasattr(ob, "evidences") else 0
    if ob.evidence_required and active and not has_evidence:
        findings.append({
            "rule": "evidence_missing", "points": w["evidence_missing"], "severity": "MEDIUM",
            "title": f"Missing evidence: {ob.evidence_required}",
            "explanation": (
                f"Obligation requires '{ob.evidence_required}' but no evidence has been "
                f"attached while status is {ob.status}."
            ),
            "obligation": ob,
            "evidence": {"evidence_required": ob.evidence_required,
                         "source_text": (ob.source_text or "")[:500], "page_number": ob.page_number},
        })

    clause = getattr(ob, "clause", None)
    if clause and clause.clause_type in ("LIABILITY", "INDEMNIFICATION") and ob.status != "REJECTED":
        findings.append({
            "rule": "liability_exposure", "points": w["liability_exposure"], "severity": "HIGH",
            "title": f"Liability exposure ({clause.clause_type.title()})",
            "explanation": (
                f"Source clause is classified {clause.clause_type} (p{clause.page_number}, "
                f"{int(clause.confidence * 100)}% confidence): {(clause.text or '')[:300]}"
            ),
            "obligation": ob,
            "evidence": {"clause_id": str(clause.id), "clause_type": clause.clause_type,
                         "source_text": (clause.text or "")[:500], "page_number": clause.page_number},
        })

    if active and ob.owner_id is None:
        findings.append({
            "rule": "no_owner", "points": w["no_owner"], "severity": "LOW",
            "title": "No owner assigned",
            "explanation": f"Obligation '{ob.title[:120]}' is {ob.status} with no owner — nobody is accountable.",
            "obligation": ob,
            "evidence": {"status": ob.status},
        })

    if ob.status == "NEEDS_REVIEW" and (today - ob.created_at.date()).days >= REVIEW_BACKLOG_DAYS:
        findings.append({
            "rule": "review_backlog", "points": w["review_backlog"], "severity": "LOW",
            "title": "Unreviewed extraction backlog",
            "explanation": (
                f"Obligation has awaited review for {(today - ob.created_at.date()).days} days "
                f"(extracted {ob.created_at.date()} via {ob.extraction_method})."
            ),
            "obligation": ob,
            "evidence": {"created_at": str(ob.created_at.date()), "extraction_method": ob.extraction_method},
        })
    return findings


def assess_contract(contract, *, today=None) -> tuple[int, list[dict]]:
    """Full assessment: obligation findings + contract-level renewal rule."""
    from deadlines.engine import today_in_tz as _today  # local alias, no cycle

    today = today or _today()
    w = weights()
    findings: list[dict] = []
    for ob in contract.obligations.select_related("clause").prefetch_related("deadlines", "evidences").all():
        findings.extend(assess_obligation(ob, today=today))

    if contract.renewal_date and contract.status not in ("TERMINATED", "ARCHIVED", "EXPIRED"):
        delta = (contract.renewal_date - today).days
        if 0 <= delta <= RENEWAL_WINDOW_DAYS:
            findings.append({
                "rule": "renewal_approaching", "points": w["renewal_approaching"], "severity": "MEDIUM",
                "title": f"Renewal approaching: {contract.renewal_date}",
                "explanation": (
                    f"Contract renews on {contract.renewal_date} ({delta} days). "
                    f"Notice and renegotiation preparation may be due."
                ),
                "obligation": None,
                "evidence": {"renewal_date": str(contract.renewal_date)},
            })
    score = min(100, sum(f["points"] for f in findings))
    return score, findings
