"""Obligation services — extraction (idempotent) + review workflow."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from audit.services import log_event
from .extractor import build_obligation_fields
from .models import Obligation


def extract_obligations_for_document(document_id, *, method: str = "RULE") -> int:
    """Build obligations from a document's clauses. Idempotent per document."""
    from clauses.models import Clause
    from documents.models import Document

    with transaction.atomic():
        doc = Document.objects.select_for_update().get(pk=document_id)
        Obligation.objects.filter(document=doc).delete()
        clauses = list(Clause.objects.filter(document=doc).order_by("page_number", "start_offset"))
        made: list[Obligation] = []
        for clause in clauses:
            fields = build_obligation_fields(clause.clause_type, clause.heading, clause.text)
            if fields is None:
                continue
            made.append(
                Obligation(
                    workspace=doc.workspace,
                    contract=doc.contract,
                    document=doc,
                    clause=clause,
                    page_number=clause.page_number,
                    source_text=clause.text,
                    confidence=clause.confidence,
                    extraction_method=method,
                    **fields,
                )
            )
        Obligation.objects.bulk_create(made)
        if made:
            log_event(
                actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
                entity_type="document", entity_id=doc.id, action="document.obligations_extracted",
                metadata={"obligations": len(made), "method": method},
            )
        return len(made)


def confirm_obligation(obligation_id, *, reviewer) -> Obligation:
    """NEEDS_REVIEW → CONFIRMED (reviewer + timestamp recorded)."""
    with transaction.atomic():
        ob = Obligation.objects.select_for_update().get(pk=obligation_id)
        if ob.status != Obligation.Status.NEEDS_REVIEW:
            raise ValueError(f"Only NEEDS_REVIEW obligations can be confirmed (current: {ob.status}).")
        ob.status = Obligation.Status.CONFIRMED
        ob.reviewer = reviewer
        ob.reviewed_at = timezone.now()
        ob.save(update_fields=["status", "reviewer", "reviewed_at", "updated_at"])
        log_event(
            actor=reviewer, organization=ob.workspace.organization, workspace=ob.workspace,
            entity_type="obligation", entity_id=ob.id, action="obligation.confirmed",
            metadata={"title": ob.title, "type": ob.obligation_type},
        )
        return ob


def reject_obligation(obligation_id, *, reviewer, reason: str = "") -> Obligation:
    with transaction.atomic():
        ob = Obligation.objects.select_for_update().get(pk=obligation_id)
        if ob.status != Obligation.Status.NEEDS_REVIEW:
            raise ValueError(f"Only NEEDS_REVIEW obligations can be rejected (current: {ob.status}).")
        ob.status = Obligation.Status.REJECTED
        ob.reviewer = reviewer
        ob.reviewed_at = timezone.now()
        ob.save(update_fields=["status", "reviewer", "reviewed_at", "updated_at"])
        log_event(
            actor=reviewer, organization=ob.workspace.organization, workspace=ob.workspace,
            entity_type="obligation", entity_id=ob.id, action="obligation.rejected",
            metadata={"title": ob.title, "reason": reason[:500]},
        )
        return ob


def activate_obligation(obligation_id, *, actor) -> Obligation:
    """CONFIRMED → ACTIVE (operational tracking begins)."""
    with transaction.atomic():
        ob = Obligation.objects.select_for_update().get(pk=obligation_id)
        if ob.status != Obligation.Status.CONFIRMED:
            raise ValueError(f"Only CONFIRMED obligations can be activated (current: {ob.status}).")
        ob.status = Obligation.Status.ACTIVE
        ob.save(update_fields=["status", "updated_at"])
        log_event(
            actor=actor, organization=ob.workspace.organization, workspace=ob.workspace,
            entity_type="obligation", entity_id=ob.id, action="obligation.activated", metadata={},
        )
        return ob
