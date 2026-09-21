"""Risk findings — one row per triggered rule, with points and explanation."""
from __future__ import annotations

import uuid

from django.db import models


class RiskFinding(models.Model):
    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="risk_findings")
    contract = models.ForeignKey("contracts.Contract", on_delete=models.CASCADE, related_name="risk_findings")
    obligation = models.ForeignKey(
        "obligations.Obligation", null=True, blank=True, on_delete=models.CASCADE, related_name="risk_findings"
    )
    rule = models.CharField(max_length=60, db_index=True)
    points = models.PositiveIntegerField(default=0)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    title = models.CharField(max_length=300)
    explanation = models.TextField()
    evidence = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-points", "-created_at"]
        indexes = [
            models.Index(fields=["workspace", "-points"]),
            models.Index(fields=["contract", "-points"]),
            models.Index(fields=["workspace", "rule"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"+{self.points} {self.rule}: {self.title[:80]}"
