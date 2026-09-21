"""Server-side audit writer — always call inside the same transaction."""
from __future__ import annotations


def log_event(*, actor=None, organization=None, workspace=None, entity_type: str, entity_id, action: str, metadata: dict | None = None):
    from audit.models import AuditEvent

    return AuditEvent.objects.create(
        actor=actor,
        organization=organization,
        workspace=workspace,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        metadata=metadata or {},
    )
