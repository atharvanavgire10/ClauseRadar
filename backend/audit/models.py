"""Append-only audit trail foundation.

The API exposes list/retrieve only — creation happens server-side via
audit.services.log_event inside transactions. No update/delete endpoints.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events"
    )
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.CASCADE, related_name="audit_events"
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace", null=True, blank=True, on_delete=models.CASCADE, related_name="audit_events"
    )
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.CharField(max_length=80, db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["workspace", "action"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.action} {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):
        # Append-only: existing rows can never be modified through the ORM.
        if not self._state.adding and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditEvent rows are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEvent rows cannot be deleted through the application.")
