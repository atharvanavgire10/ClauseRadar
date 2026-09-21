"""Workspace-scoped permission helpers — the tenant isolation boundary."""
from __future__ import annotations

from rest_framework import permissions


def user_workspace_ids(user) -> set:
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return set()  # handled separately
    from workspaces.models import WorkspaceMembership

    return set(
        WorkspaceMembership.objects.filter(user=user).values_list("workspace_id", flat=True)
    )


def user_can_access_workspace(user, workspace) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    from workspaces.models import WorkspaceMembership

    return WorkspaceMembership.objects.filter(user=user, workspace=workspace).exists()


def user_can_write_workspace(user, workspace) -> bool:
    """VIEWER is read-only; all other member roles may write."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    from workspaces.models import WorkspaceMembership

    try:
        m = WorkspaceMembership.objects.get(user=user, workspace=workspace)
    except WorkspaceMembership.DoesNotExist:
        return False
    return m.role in {"OWNER", "ADMIN", "MEMBER"}


class IsWorkspaceMember(permissions.BasePermission):
    """Object-level guard: obj must expose `.workspace` (or be a Workspace)."""

    def has_object_permission(self, request, view, obj) -> bool:
        from workspaces.models import Workspace

        workspace = obj if isinstance(obj, Workspace) else getattr(obj, "workspace", None)
        if workspace is None:
            return False
        return user_can_access_workspace(request.user, workspace)
