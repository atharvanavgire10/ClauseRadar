"""Deadlines — computed dates with derived statuses (never stale, never guessed)."""
from __future__ import annotations

import uuid

from django.db import models


class Deadline(models.Model):
    class Kind(models.TextChoices):
        FIXED = "FIXED", "Fixed date"
        RELATIVE = "RELATIVE", "Relative to anchor"
        RENEWAL = "RENEWAL", "Renewal"
        RENEWAL_NOTICE = "RENEWAL_NOTICE", "Renewal notice"
        EXPIRY = "EXPIRY", "Contract expiry"
        RECURRING = "RECURRING", "Recurring instance"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="deadlines")
    contract = models.ForeignKey("contracts.Contract", on_delete=models.CASCADE, related_name="deadlines")
    obligation = models.ForeignKey(
        "obligations.Obligation", null=True, blank=True, on_delete=models.CASCADE, related_name="deadlines"
    )
    title = models.CharField(max_length=300)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.FIXED, db_index=True)
    due_date = models.DateField(db_index=True)
    anchor_date = models.DateField(null=True, blank=True, help_text="Anchor the offset was computed from.")
    offset_days = models.IntegerField(null=True, blank=True)
    business_days = models.BooleanField(default=False)
    rule = models.CharField(max_length=500, blank=True, help_text="Human-readable derivation, e.g. '60 days before renewal 2026-12-15'.")
    completed = models.BooleanField(default=False, db_index=True)
    waived = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "created_at"]
        indexes = [
            models.Index(fields=["workspace", "due_date"]),
            models.Index(fields=["contract", "due_date"]),
            models.Index(fields=["obligation", "due_date"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.title} due {self.due_date}"
