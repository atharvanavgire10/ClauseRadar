"""Scheduled operations for the Vercel deployment (replaces Celery Beat).

Vercel Cron invokes these endpoints (GET — Vercel crons issue GET requests;
POST is accepted too). Authentication is a shared secret: Vercel sends
`Authorization: Bearer <CRON_SECRET>` automatically when CRON_SECRET is set
on the project. No workspace data is exposed; execution is idempotent because
the underlying services are (update_or_create generation, per-day dedupe keys).
"""
from __future__ import annotations

import hmac

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from audit.services import log_event


def _authorized(request) -> bool:
    secret = getattr(settings, "CRON_SECRET", "")
    if not secret:
        return False
    header = request.headers.get("Authorization", "")
    return hmac.compare_digest(header, f"Bearer {secret}")


def _deny():
    return Response({"detail": "Forbidden.", "code": "forbidden"}, status=403)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def recurring_deadlines(request):
    if not _authorized(request):
        return _deny()
    from deadlines.services import generate_recurring_for_workspace
    from workspaces.models import Workspace

    total, workspaces = 0, 0
    for ws in Workspace.objects.all():
        total += generate_recurring_for_workspace(str(ws.id))
        workspaces += 1
        log_event(actor=None, organization=ws.organization, workspace=ws,
                  entity_type="workspace", entity_id=ws.id,
                  action="cron.recurring_generated",
                  metadata={"workspace": str(ws.id)})
    return Response({"ok": True, "job": "recurring-deadlines",
                     "workspaces": workspaces, "deadlines": total})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def deadline_scan(request):
    if not _authorized(request):
        return _deny()
    from notifications.services import notify_deadline_scan
    from workspaces.models import Workspace

    total, workspaces = 0, 0
    for ws in Workspace.objects.all():
        total += notify_deadline_scan(workspace=ws)
        workspaces += 1
        log_event(actor=None, organization=ws.organization, workspace=ws,
                  entity_type="workspace", entity_id=ws.id,
                  action="cron.deadline_scan",
                  metadata={"workspace": str(ws.id), "notifications": total})
    return Response({"ok": True, "job": "deadline-scan",
                     "workspaces": workspaces, "notifications": total})
