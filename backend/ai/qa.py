"""Evidence-grounded Q&A — deterministic retrieval over workspace data.

Every answer is composed from retrieved rows; every factual claim carries a
citation (document, page, clause, source text). When nothing relevant is
found the answer says so explicitly instead of hallucinating.
"""
from __future__ import annotations

import re

INSUFFICIENT = "Insufficient evidence in the available documents."

INTENTS: list[tuple[str, str]] = [
    ("insurance", r"insur"),
    ("renewal", r"renew"),
    ("overdue", r"overdue|past due|late\b"),
    ("termination", r"terminat"),
    ("payment", r"payment|pay\b|invoice"),
    ("reporting", r"report"),
    ("deadlines", r"deadline|due\b|expir"),
    ("obligations", r"obligation|duties|must|shall|required"),
]


def detect_intent(question: str) -> str:
    q = question.lower()
    for intent, pattern in INTENTS:
        if re.search(pattern, q):
            return intent
    return "general"


def _cite_obligation(ob) -> dict:
    doc = getattr(ob, "document", None)
    return {
        "document_id": str(doc.id) if doc else None,
        "document_name": doc.original_filename if doc else None,
        "page_number": ob.page_number,
        "clause_id": str(ob.clause_id) if ob.clause_id else None,
        "obligation_id": str(ob.id),
        "contract_id": str(ob.contract_id),
        "source_text": (ob.source_text or "")[:300],
    }


def _cite_deadline(dl) -> dict:
    return {
        "document_id": None,
        "document_name": None,
        "page_number": None,
        "clause_id": None,
        "obligation_id": str(dl.obligation_id) if dl.obligation_id else None,
        "source_text": f"{dl.title} — due {dl.due_date}. {dl.rule}",
        "deadline_id": str(dl.id),
        "contract_id": str(dl.contract_id),
    }


def _cite_clause(cl) -> dict:
    return {
        "document_id": str(cl.document_id),
        "document_name": getattr(cl.document, "original_filename", None),
        "page_number": cl.page_number,
        "clause_id": str(cl.id),
        "obligation_id": None,
        "source_text": (cl.text or "")[:300],
    }


def answer(*, workspace, question: str, contract_id: str | None = None) -> dict:
    """Answer a question with citations. Workspace-scoped; never invents."""
    from clauses.models import Clause
    from deadlines.engine import today_in_tz
    from deadlines.models import Deadline
    from obligations.models import Obligation

    intent = detect_intent(question)
    citations: list[dict] = []
    lines: list[str] = []

    obs = Obligation.objects.filter(workspace=workspace).select_related("document", "contract")
    dls = Deadline.objects.filter(workspace=workspace).select_related("contract")
    cls = Clause.objects.filter(workspace=workspace).select_related("document")
    if contract_id:
        obs, dls, cls = obs.filter(contract_id=contract_id), dls.filter(contract_id=contract_id), cls.filter(contract_id=contract_id)

    if intent == "insurance":
        matches = list(obs.filter(obligation_type="INSURANCE").exclude(status="REJECTED")[:10])
        if not matches:
            return {"answer": INSUFFICIENT, "citations": [], "intent": intent}
        lines.append(f"Found {len(matches)} insurance obligation(s):")
        for ob in matches:
            lines.append(f"- {ob.title} [{ob.status}] (p{ob.page_number})")
            citations.append(_cite_obligation(ob))
    elif intent == "renewal":
        matches = list(dls.filter(kind__in=("RENEWAL", "RENEWAL_NOTICE")).order_by("due_date")[:10])
        if not matches:
            return {"answer": INSUFFICIENT, "citations": [], "intent": intent}
        lines.append("Renewal deadlines:")
        for dl in matches:
            lines.append(f"- {dl.title}: due {dl.due_date} ({dl.rule})")
            citations.append(_cite_deadline(dl))
    elif intent == "overdue":
        today = today_in_tz()
        matches = list(dls.filter(due_date__lt=today, completed=False, waived=False).order_by("due_date")[:10])
        if not matches:
            return {"answer": "No overdue deadlines found in the available documents.", "citations": [], "intent": intent}
        lines.append(f"Found {len(matches)} overdue deadline(s):")
        for dl in matches:
            lines.append(f"- {dl.title}: was due {dl.due_date}")
            citations.append(_cite_deadline(dl))
    elif intent == "termination":
        matches = list(cls.filter(clause_type="TERMINATION")[:5]) + list(
            obs.filter(obligation_type="TERMINATION_NOTICE").exclude(status="REJECTED")[:5])
        if not matches:
            return {"answer": INSUFFICIENT, "citations": [], "intent": intent}
        lines.append("Termination provisions:")
        for m in matches:
            if isinstance(m, Obligation):
                lines.append(f"- {m.title} [{m.status}]")
                citations.append(_cite_obligation(m))
            else:
                lines.append(f"- {(m.heading or 'Termination clause')} (p{m.page_number})")
                citations.append(_cite_clause(m))
    elif intent == "payment":
        matches = list(obs.filter(obligation_type="PAYMENT").exclude(status="REJECTED")[:10])
        if not matches:
            return {"answer": INSUFFICIENT, "citations": [], "intent": intent}
        lines.append(f"Found {len(matches)} payment obligation(s):")
        for ob in matches:
            lines.append(f"- {ob.title} [{ob.status}]")
            citations.append(_cite_obligation(ob))
    elif intent == "reporting":
        matches = list(obs.filter(obligation_type="REPORTING").exclude(status="REJECTED")[:10])
        if not matches:
            return {"answer": INSUFFICIENT, "citations": [], "intent": intent}
        lines.append(f"Found {len(matches)} reporting obligation(s):")
        for ob in matches:
            lines.append(f"- {ob.title} [{ob.status}] ({ob.frequency})")
            citations.append(_cite_obligation(ob))
    elif intent in ("deadlines", "obligations", "general"):
        total = obs.exclude(status="REJECTED").count()
        if total == 0:
            return {"answer": INSUFFICIENT, "citations": [], "intent": intent}
        by_status: dict[str, int] = {}
        for ob in obs.exclude(status="REJECTED"):
            by_status[ob.status] = by_status.get(ob.status, 0) + 1
        lines.append(f"{total} tracked obligation(s): " + ", ".join(f"{v} {k}" for k, v in sorted(by_status.items())))
        for ob in obs.exclude(status="REJECTED").order_by("-created_at")[:5]:
            lines.append(f"- {ob.title} [{ob.status}]")
            citations.append(_cite_obligation(ob))

    scope = "the selected contract" if contract_id else "the workspace"
    return {"answer": "\n".join(lines) + f"\n\nBased on {len(citations)} cited source(s) in {scope}.",
            "citations": citations, "intent": intent}
