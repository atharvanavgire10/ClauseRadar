"""Obligations — structured, evidence-backed operational duties.

Lifecycle: NEEDS_REVIEW → CONFIRMED / REJECTED → ACTIVE → IN_PROGRESS → COMPLETED
(plus WAIVED). Every obligation begins as NEEDS_REVIEW and links to its source.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Obligation(models.Model):
    class Type(models.TextChoices):
        INSURANCE = "INSURANCE", "Insurance"
        PAYMENT = "PAYMENT", "Payment"
        REPORTING = "REPORTING", "Reporting"
        RENEWAL_NOTICE = "RENEWAL_NOTICE", "Renewal notice"
        TERMINATION_NOTICE = "TERMINATION_NOTICE", "Termination notice"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        SLA = "SLA", "SLA"
        CONFIDENTIALITY = "CONFIDENTIALITY", "Confidentiality"
        SECURITY = "SECURITY", "Security"
        AUDIT = "AUDIT", "Audit"
        DELIVERY = "DELIVERY", "Delivery"
        GENERAL = "GENERAL", "General"

    class Status(models.TextChoices):
        NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"
        ACTIVE = "ACTIVE", "Active"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        WAIVED = "WAIVED", "Waived"

    class Frequency(models.TextChoices):
        ONE_TIME = "ONE_TIME", "One time"
        CONTINUOUS = "CONTINUOUS", "Continuous"
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        SEMI_ANNUAL = "SEMI_ANNUAL", "Semi-annual"
        ANNUAL = "ANNUAL", "Annual"
        CUSTOM = "CUSTOM", "Custom"

    class Method(models.TextChoices):
        RULE = "RULE", "Rule"
        LLM = "LLM", "LLM"
        HYBRID = "HYBRID", "Hybrid"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="obligations")
    contract = models.ForeignKey("contracts.Contract", on_delete=models.CASCADE, related_name="obligations")
    document = models.ForeignKey(
        "documents.Document", null=True, blank=True, on_delete=models.SET_NULL, related_name="obligations"
    )
    clause = models.ForeignKey(
        "clauses.Clause", null=True, blank=True, on_delete=models.SET_NULL, related_name="obligations"
    )
    page_number = models.PositiveIntegerField(default=1)
    source_text = models.TextField(help_text="Exact evidence text backing this obligation.")
    title = models.CharField(max_length=300)
    obligation_type = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERAL, db_index=True)
    actor = models.CharField(max_length=120, blank=True, help_text="Party bound (e.g. Vendor).")
    action = models.CharField(max_length=300, blank=True)
    requirement = models.CharField(max_length=500, blank=True)
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.ONE_TIME)
    evidence_required = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEEDS_REVIEW, db_index=True)
    confidence = models.FloatField(default=0.5)
    extraction_method = models.CharField(max_length=10, choices=Method.choices, default=Method.RULE)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_obligations"
    )
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    notes = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_obligations"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["contract", "status"]),
            models.Index(fields=["workspace", "obligation_type"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.obligation_type} [{self.status}]: {self.title[:80]}"
