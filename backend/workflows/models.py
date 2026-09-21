"""Operational tracking — comments, evidence attachments, tasks."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="comments")
    contract = models.ForeignKey(
        "contracts.Contract", null=True, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    obligation = models.ForeignKey(
        "obligations.Obligation", null=True, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="comments"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["workspace", "created_at"]),
            models.Index(fields=["obligation", "created_at"]),
            models.Index(fields=["contract", "created_at"]),
        ]


class Evidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="evidences")
    obligation = models.ForeignKey(
        "obligations.Obligation", on_delete=models.CASCADE, related_name="evidences"
    )
    file = models.FileField(upload_to="evidence/%Y/%m/", max_length=500)
    original_filename = models.CharField(max_length=300)
    mime = models.CharField(max_length=120)
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, db_index=True)
    note = models.CharField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_evidence"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["obligation", "-created_at"])]


class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="tasks")
    contract = models.ForeignKey(
        "contracts.Contract", null=True, blank=True, on_delete=models.CASCADE, related_name="tasks"
    )
    obligation = models.ForeignKey(
        "obligations.Obligation", null=True, blank=True, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=300)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tasks"
    )
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["contract", "status"]),
        ]
