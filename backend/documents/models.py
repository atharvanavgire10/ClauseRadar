"""Documents — uploaded contract files + extracted pages.

States: UPLOADED → PROCESSING → READY | FAILED.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="documents")
    contract = models.ForeignKey("contracts.Contract", on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="documents/%Y/%m/", max_length=500)
    original_filename = models.CharField(max_length=300)
    mime = models.CharField(max_length=120, db_index=True)
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    page_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    ocr_used = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["contract", "-created_at"]),
            models.Index(fields=["workspace", "sha256"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.original_filename} [{self.status}]"


class DocumentPage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveIntegerField(db_index=True)
    text = models.TextField(blank=True)
    char_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["page_number"]
        constraints = [
            models.UniqueConstraint(fields=["document", "page_number"], name="uniq_document_page"),
        ]
        indexes = [models.Index(fields=["document", "page_number"])]

    def save(self, *args, **kwargs):
        self.char_count = len(self.text or "")
        super().save(*args, **kwargs)
