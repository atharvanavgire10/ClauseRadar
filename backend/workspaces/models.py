"""Workspace — the tenant boundary. All domain objects belong to a workspace."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Workspace(models.Model):
    class Type(models.TextChoices):
        STANDARD = "STANDARD", "Standard"
        PUBLIC_EVAL = "PUBLIC_EVAL", "Public evaluation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="workspaces"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, db_index=True)
    workspace_type = models.CharField(max_length=16, choices=Type.choices, default=Type.STANDARD, db_index=True)
    public_slug = models.SlugField(max_length=220, null=True, blank=True, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_workspaces"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="uniq_workspace_slug_per_org"),
        ]
        indexes = [
            models.Index(fields=["organization", "slug"]),
            models.Index(fields=["workspace_type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.organization.slug}/{self.slug}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or "workspace"
            slug, i = base, 1
            while (
                Workspace.objects.filter(organization=self.organization, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)


class WorkspaceMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"
        VIEWER = "VIEWER", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace", "user"], name="uniq_workspace_member"),
        ]
        indexes = [models.Index(fields=["workspace", "user"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user} @ {self.workspace} ({self.role})"
