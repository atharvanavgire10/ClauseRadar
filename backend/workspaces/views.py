from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import log_event
from core.permissions import user_can_write_workspace
from .models import Workspace, WorkspaceMembership
from .serializers import WorkspaceMembershipSerializer, WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["organization", "workspace_type", "slug"]
    search_fields = ["name", "slug"]
    ordering_fields = ["created_at", "name"]

    def get_queryset(self):
        user = self.request.user
        qs = Workspace.objects.select_related("organization").all()
        if user.is_superuser:
            return qs
        return qs.filter(memberships__user=user).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.save(created_by=self.request.user)
        WorkspaceMembership.objects.create(workspace=workspace, user=self.request.user, role="OWNER")
        log_event(
            actor=self.request.user,
            organization=workspace.organization,
            workspace=workspace,
            entity_type="workspace",
            entity_id=workspace.id,
            action="workspace.created",
            metadata={"name": workspace.name},
        )

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        workspace = self.get_object()
        memberships = WorkspaceMembership.objects.filter(workspace=workspace).select_related("user")
        return Response(WorkspaceMembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        from django.contrib.auth import get_user_model

        workspace = self.get_object()
        if not user_can_write_workspace(request.user, workspace):
            return Response({"detail": "Permission denied.", "code": "forbidden"}, status=403)
        email = (request.data.get("email") or "").strip().lower()
        role = request.data.get("role", "MEMBER")
        if role not in {"OWNER", "ADMIN", "MEMBER", "VIEWER"}:
            return Response({"detail": "Invalid role.", "code": "validation_error"}, status=400)
        User = get_user_model()
        try:
            target = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found.", "code": "not_found"}, status=404)
        WorkspaceMembership.objects.update_or_create(
            workspace=workspace, user=target, defaults={"role": role}
        )
        log_event(
            actor=request.user, organization=workspace.organization, workspace=workspace,
            entity_type="workspace", entity_id=workspace.id, action="workspace.member_added",
            metadata={"email": email, "role": role},
        )
        return Response({"detail": "Member added."}, status=200)
