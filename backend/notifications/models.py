"""Notifications — in-app rows + email abstraction + per-user preferences."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        DEADLINE_APPROACHING = "deadline_approaching", "Deadline approaching"
        OBLIGATION_OVERDUE = "obligation_overdue", "Obligation overdue"
        CONTRACT_PROCESSED = "contract_processed", "Contract processed"
        OBLIGATION_ASSIGNED = "obligation_assigned", "Obligation assigned"
        RISK_INCREASED = "risk_increased", "Risk increased"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30, choices=Kind.choices, db_index=True)
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=80, blank=True)
    dedupe_key = models.CharField(max_length=200, blank=True, db_index=True)
    read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "read", "-created_at"]),
            models.Index(fields=["workspace", "kind"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.kind} → {self.user}: {self.title[:60]}"


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_prefs")
    kind = models.CharField(max_length=30, choices=Notification.Kind.choices, db_index=True)
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "kind"], name="uniq_notif_pref"),
        ]
