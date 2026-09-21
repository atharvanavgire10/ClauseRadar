"""Clauses — deterministic, evidence-linked segments of source documents."""
from __future__ import annotations

import uuid

from django.db import models


class Clause(models.Model):
    class Type(models.TextChoices):
        DEFINITIONS = "DEFINITIONS", "Definitions"
        PAYMENT = "PAYMENT", "Payment"
        RENEWAL = "RENEWAL", "Renewal"
        TERMINATION = "TERMINATION", "Termination"
        INSURANCE = "INSURANCE", "Insurance"
        CONFIDENTIALITY = "CONFIDENTIALITY", "Confidentiality"
        SECURITY = "SECURITY", "Security"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        SLA = "SLA", "SLA"
        REPORTING = "REPORTING", "Reporting"
        AUDIT = "AUDIT", "Audit"
        LIABILITY = "LIABILITY", "Liability"
        INDEMNIFICATION = "INDEMNIFICATION", "Indemnification"
        NOTICE = "NOTICE", "Notice"
        DELIVERY = "DELIVERY", "Delivery"
        GENERAL = "GENERAL", "General"

    class Method(models.TextChoices):
        RULE = "RULE", "Rule"
        LLM = "LLM", "LLM"
        HYBRID = "HYBRID", "Hybrid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="clauses")
    contract = models.ForeignKey("contracts.Contract", on_delete=models.CASCADE, related_name="clauses")
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="clauses")
    page = models.ForeignKey(
        "documents.DocumentPage", null=True, blank=True, on_delete=models.SET_NULL, related_name="clauses"
    )
    page_number = models.PositiveIntegerField(db_index=True, default=1)
    heading = models.CharField(max_length=300, blank=True)
    text = models.TextField()
    clause_type = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERAL, db_index=True)
    start_offset = models.PositiveIntegerField(default=0)
    end_offset = models.PositiveIntegerField(default=0)
    confidence = models.FloatField(default=0.5)
    extraction_method = models.CharField(max_length=10, choices=Method.choices, default=Method.RULE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["document_id", "page_number", "start_offset"]
        indexes = [
            models.Index(fields=["workspace", "clause_type"]),
            models.Index(fields=["contract", "clause_type"]),
            models.Index(fields=["document", "page_number"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.clause_type} p{self.page_number}: {(self.heading or self.text[:60])}"
