"""Deadline generation + transitions. Generation only creates dated deadlines
when an anchor date exists (explicit date in text, or contract renewal/end
dates). Unknown anchors are skipped — dates are never invented."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from audit.services import log_event
from .engine import (
    DEFAULT_RENEWAL_NOTICE_DAYS,
    RECURRING_FREQUENCIES,
    occurrence_dates,
    parse_explicit_date,
    parse_relative,
    renewal_notice_date,
    today_in_tz,
)
from .models import Deadline


def _upsert(*, workspace, contract, obligation, title, kind, due_date,
            anchor_date=None, offset_days=None, business_days=False, rule="") -> tuple[Deadline, bool]:
    return Deadline.objects.update_or_create(
        workspace=workspace, contract=contract, obligation=obligation, title=title, kind=kind,
        defaults={"due_date": due_date, "anchor_date": anchor_date, "offset_days": offset_days,
                  "business_days": business_days, "rule": rule[:500]},
    )


def generate_for_contract(contract_id) -> int:
    """Contract-level deadlines: renewal, renewal notice, expiry. Returns count."""
    from contracts.models import Contract

    from .engine import parse_relative as _pr  # noqa: F401  (kept local for clarity)

    contract = Contract.objects.select_related("workspace").get(pk=contract_id)
    ws = contract.workspace
    made = 0

    notice_days = DEFAULT_RENEWAL_NOTICE_DAYS
    # Prefer notice periods stated in the contract's own obligations.
    from obligations.models import Obligation

    for ob in Obligation.objects.filter(contract=contract).exclude(status="REJECTED"):
        rel = parse_relative(ob.source_text or "")
        if rel and rel["direction"] == "before" and "renew" in (ob.source_text or "").lower():
            notice_days = rel["days"]
            break

    if contract.renewal_date:
        _, created = _upsert(
            workspace=ws, contract=contract, obligation=None,
            title=f"Renewal: {contract.title}", kind=Deadline.Kind.RENEWAL,
            due_date=contract.renewal_date,
            rule=f"contract renewal date {contract.renewal_date}",
        )
        made += created
        notice_due = renewal_notice_date(contract.renewal_date, notice_days)
        _, created = _upsert(
            workspace=ws, contract=contract, obligation=None,
            title=f"Renewal notice: {contract.title}", kind=Deadline.Kind.RENEWAL_NOTICE,
            due_date=notice_due, anchor_date=contract.renewal_date, offset_days=notice_days,
            rule=f"{notice_days} days before renewal {contract.renewal_date}",
        )
        made += created
    if contract.end_date and contract.end_date != contract.renewal_date:
        _, created = _upsert(
            workspace=ws, contract=contract, obligation=None,
            title=f"Expiry: {contract.title}", kind=Deadline.Kind.EXPIRY,
            due_date=contract.end_date, rule=f"contract end date {contract.end_date}",
        )
        made += created

    if made:
        log_event(actor=None, organization=ws.organization, workspace=ws,
                  entity_type="contract", entity_id=contract.id,
                  action="contract.deadlines_generated", metadata={"deadlines": made})
    return made


def generate_for_obligation(obligation_id) -> int:
    """Obligation-level deadlines from explicit dates in source text."""
    from obligations.models import Obligation

    ob = Obligation.objects.select_related("workspace", "contract").get(pk=obligation_id)
    made = 0
    explicit = parse_explicit_date(ob.source_text or "")
    if explicit:
        _, created = _upsert(
            workspace=ob.workspace, contract=ob.contract, obligation=ob,
            title=f"Due: {ob.title[:200]}", kind=Deadline.Kind.FIXED,
            due_date=explicit, rule=f"explicit date {explicit} in source text",
        )
        made += created
    return made


def generate_for_workspace_contracts(workspace_id) -> int:
    from contracts.models import Contract

    total = 0
    for contract in Contract.objects.filter(workspace_id=workspace_id):
        total += generate_for_contract(contract.id)
        from obligations.models import Obligation

        for ob in Obligation.objects.filter(contract=contract):
            total += generate_for_obligation(ob.id)
    return total


def generate_recurring_for_obligation(obligation_id, *, occurrences: int = 6) -> int:
    """Generate future RECURRING deadlines for a recurring obligation.

    Idempotent: update_or_create on (obligation, due_date, kind) — retries and
    overlapping beat runs never duplicate. Anchor: contract start date, else
    today. ONE_TIME/CONTINUOUS/CUSTOM frequencies yield zero.
    """
    from obligations.models import Obligation

    ob = Obligation.objects.select_related("workspace", "contract").get(pk=obligation_id)
    if ob.frequency not in RECURRING_FREQUENCIES:
        return 0
    if ob.status in ("REJECTED", "COMPLETED", "WAIVED"):
        return 0
    anchor = ob.contract.start_date or today_in_tz()
    dates = occurrence_dates(ob.frequency, anchor, today=today_in_tz(), count=occurrences)
    made = 0
    for due in dates:
        _, created = Deadline.objects.update_or_create(
            workspace=ob.workspace, contract=ob.contract, obligation=ob,
            title=f"Recurring: {ob.title[:200]}", kind=Deadline.Kind.RECURRING,
            due_date=due,
            defaults={"anchor_date": anchor,
                      "rule": f"{ob.frequency} occurrence from anchor {anchor}"[:500]},
        )
        made += created
    if made:
        log_event(actor=None, organization=ob.workspace.organization, workspace=ob.workspace,
                  entity_type="obligation", entity_id=ob.id,
                  action="obligation.recurring_generated",
                  metadata={"deadlines": made, "frequency": ob.frequency})
    return made


def generate_recurring_for_workspace(workspace_id, *, occurrences: int = 6) -> int:
    from obligations.models import Obligation

    total = 0
    for ob in Obligation.objects.filter(workspace_id=workspace_id).exclude(
        status__in=("REJECTED", "COMPLETED", "WAIVED")
    ):
        total += generate_recurring_for_obligation(ob.id, occurrences=occurrences)
    return total


def set_completed(deadline_id, *, actor, completed: bool = True):
    with transaction.atomic():
        dl = Deadline.objects.select_for_update().get(pk=deadline_id)
        dl.completed = completed
        if completed:
            dl.waived = False
            dl.completed_at = timezone.now()
        else:
            dl.completed_at = None
        dl.save(update_fields=["completed", "waived", "completed_at", "updated_at"])
        log_event(actor=actor, organization=dl.workspace.organization, workspace=dl.workspace,
                  entity_type="deadline", entity_id=dl.id,
                  action="deadline.completed" if completed else "deadline.reopened",
                  metadata={"title": dl.title, "due": str(dl.due_date)})
        return dl


def set_waived(deadline_id, *, actor, waived: bool = True):
    with transaction.atomic():
        dl = Deadline.objects.select_for_update().get(pk=deadline_id)
        dl.waived = waived
        if waived:
            dl.completed = False
            dl.completed_at = None
        dl.save(update_fields=["waived", "completed", "completed_at", "updated_at"])
        log_event(actor=actor, organization=dl.workspace.organization, workspace=dl.workspace,
                  entity_type="deadline", entity_id=dl.id,
                  action="deadline.waived" if waived else "deadline.unwaived",
                  metadata={"title": dl.title, "due": str(dl.due_date)})
        return dl
