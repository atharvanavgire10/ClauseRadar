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
        for ob in Obligation.objects.filter(document=doc):
            log_event(
                actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
                entity_type="obligation", entity_id=ob.id, action="obligation.created",
                metadata={"title": ob.title, "type": ob.obligation_type,
                          "extraction_method": method, "document": str(doc.id)},
            )
        # Obligation-level dated deadlines from explicit dates (best-effort).
        try:
            from deadlines.services import generate_for_obligation

            for ob in Obligation.objects.filter(document=doc):
                generate_for_obligation(ob.id)
        except Exception:  # pragma: no cover
            pass
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
        try:
            from deadlines.services import generate_recurring_for_obligation

            generate_recurring_for_obligation(ob.id)
        except Exception:  # pragma: no cover - recurrence must never break activation
            pass
        try:
            from risks.services import assess_contract_risks

            assess_contract_risks(ob.contract_id)
        except Exception:  # pragma: no cover - risk must never break activation
            pass
        return ob


def _transition(obligation_id, *, actor, from_statuses: tuple, to_status: str,
                action: str, extra: dict | None = None) -> Obligation:
    with transaction.atomic():
        ob = Obligation.objects.select_for_update().get(pk=obligation_id)
        if ob.status not in from_statuses:
            raise ValueError(f"Cannot move {ob.status} → {to_status}.")
        ob.status = to_status
        ob.save(update_fields=["status", "updated_at"])
        log_event(
            actor=actor, organization=ob.workspace.organization, workspace=ob.workspace,
            entity_type="obligation", entity_id=ob.id, action=action,
            metadata={"title": ob.title, **(extra or {})},
        )
        return ob


def start_progress(obligation_id, *, actor) -> Obligation:
    return _transition(obligation_id, actor=actor, from_statuses=("ACTIVE",), to_status="IN_PROGRESS",
                       action="obligation.started")


def complete_obligation(obligation_id, *, actor) -> Obligation:
    return _transition(obligation_id, actor=actor, from_statuses=("ACTIVE", "IN_PROGRESS"),
                       to_status="COMPLETED", action="obligation.completed")


def reopen_obligation(obligation_id, *, actor) -> Obligation:
    return _transition(obligation_id, actor=actor, from_statuses=("COMPLETED", "WAIVED"),
                       to_status="ACTIVE", action="obligation.reopened")


def waive_obligation(obligation_id, *, actor, reason: str = "") -> Obligation:
    return _transition(obligation_id, actor=actor,
                       from_statuses=("NEEDS_REVIEW", "CONFIRMED", "ACTIVE", "IN_PROGRESS"),
                       to_status="WAIVED", action="obligation.waived",
                       extra={"reason": reason[:500]})


def assign_owner(obligation_id, *, actor, owner) -> Obligation:
    """Assign (or unassign with owner=None). Owner should belong to the workspace;
    enforced at the API layer where membership is visible."""
    with transaction.atomic():
        ob = Obligation.objects.select_for_update().get(pk=obligation_id)
        previous = str(ob.owner_id)
        ob.owner = owner
        ob.save(update_fields=["owner", "updated_at"])
        log_event(
            actor=actor, organization=ob.workspace.organization, workspace=ob.workspace,
            entity_type="obligation", entity_id=ob.id, action="obligation.owner_changed",
            metadata={"previous": previous, "owner": str(getattr(owner, "id", None))},
        )
        try:
            from notifications.services import notify_obligation_assigned

            notify_obligation_assigned(obligation=ob, actor=actor)
        except Exception:  # pragma: no cover - notifications must never break assignment
            pass
        return ob
