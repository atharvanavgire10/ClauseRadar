"""Notification fan-out — workspace recipients, prefs, dedupe, async email."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .email import send_notification_email
from .models import Notification, NotificationPreference


def prefs_for(user, kind: str) -> tuple[bool, bool]:
    try:
        pref = NotificationPreference.objects.get(user=user, kind=kind)
        return pref.in_app, pref.email
    except NotificationPreference.DoesNotExist:
        return True, True


def _create(*, workspace, user, kind, title, body="", entity_type="", entity_id="",
            dedupe_key="", send_email=True) -> Notification | None:
    in_app, want_email = prefs_for(user, kind)
    if not in_app and not want_email:
        return None
    with transaction.atomic():
        if dedupe_key and Notification.objects.filter(
            workspace=workspace, user=user, dedupe_key=dedupe_key
        ).exists():
            return None  # idempotent: already notified
        notif = Notification.objects.create(
            workspace=workspace, user=user, kind=kind, title=title[:300], body=body,
            entity_type=entity_type, entity_id=str(entity_id),
            dedupe_key=dedupe_key[:200],
        )
        if not in_app:
            # Email-only preference: keep row for history but could hide; we keep it.
            pass
        emailed = False
        if send_email and want_email and user.email:
            emailed = send_notification_email(user.email, title, body or title)
        notif.email_sent = emailed
        notif.save(update_fields=["email_sent"])
        return notif


def workspace_managers(workspace):
    """OWNER/ADMIN members — recipients for contract-level events."""
    from workspaces.models import WorkspaceMembership

    return [m.user for m in WorkspaceMembership.objects.filter(
        workspace=workspace, role__in=("OWNER", "ADMIN")).select_related("user")]


def notify_contract_processed(*, workspace, actor, contract, document) -> int:
    made = 0
    for recipient in workspace_managers(workspace):
        if actor and recipient.id == actor.id:
            continue
        n = _create(
            workspace=workspace, user=recipient, kind="contract_processed",
            title=f"Document ready: {document.original_filename}",
            body=f"'{contract.title}' finished processing: {document.page_count} pages, clauses extracted.",
            entity_type="document", entity_id=document.id,
            dedupe_key=f"processed:{document.id}",
        )
        made += 1 if n else 0
    return made


def notify_obligation_assigned(*, obligation, actor) -> int:
    if obligation.owner_id is None:
        return 0
    n = _create(
        workspace=obligation.workspace, user=obligation.owner,
        kind="obligation_assigned",
        title=f"Assigned: {obligation.title[:200]}",
        body=f"You were assigned '{obligation.title}' in contract '{obligation.contract.title}'.",
        entity_type="obligation", entity_id=obligation.id,
        dedupe_key=f"assigned:{obligation.id}:{obligation.owner_id}",
    )
    return 1 if n else 0


def notify_deadline_scan(*, workspace) -> int:
    """DUE_SOON + OVERDUE deadlines → manager notifications (dedupe per day)."""
    from deadlines.engine import today_in_tz
    from deadlines.models import Deadline

    today = today_in_tz()
    made = 0
    due_soon = Deadline.objects.filter(
        workspace=workspace, due_date__gte=today,
        due_date__lte=today + timezone.timedelta(days=7),
        completed=False, waived=False,
    ).select_related("contract")
    overdue = Deadline.objects.filter(
        workspace=workspace, due_date__lt=today, completed=False, waived=False,
    ).select_related("contract")
    for dl in list(due_soon) + list(overdue):
        kind = "obligation_overdue" if dl.due_date < today else "deadline_approaching"
        for recipient in workspace_managers(workspace):
            n = _create(
                workspace=workspace, user=recipient, kind=kind,
                title=f"{'Overdue' if kind == 'obligation_overdue' else 'Due soon'}: {dl.title[:200]}",
                body=f"'{dl.title}' is due {dl.due_date}. {dl.rule}",
                entity_type="deadline", entity_id=dl.id,
                dedupe_key=f"{kind}:{dl.id}:{today.isoformat()}",
            )
            made += 1 if n else 0
    return made


def notify_risk_increased(*, workspace, contract, score: int, previous: int | None = None) -> int:
    """Notify managers when a contract scores HIGH/CRITICAL (dedupe per score band per day)."""
    from deadlines.engine import today_in_tz
    from risks.rules import level_for

    level = level_for(score)
    if level not in ("HIGH", "CRITICAL"):
        return 0
    if previous is not None and level_for(previous) == level:
        return 0  # no band change → no new notification
    made = 0
    for recipient in workspace_managers(workspace):
        n = _create(
            workspace=workspace, user=recipient, kind="risk_increased",
            title=f"Risk {level}: {contract.title} scores {score}",
            body=f"Latest assessment scores '{contract.title}' at {score} ({level}). Review findings in Risk Radar.",
            entity_type="contract", entity_id=contract.id,
            dedupe_key=f"risk:{contract.id}:{level}:{today_in_tz().isoformat()}",
        )
        made += 1 if n else 0
    return made
