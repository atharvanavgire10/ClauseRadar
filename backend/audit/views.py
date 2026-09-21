"""Read-only audit API — append-only by design (no POST/PUT/PATCH/DELETE)."""
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "organization", "entity_type", "action"]
    search_fields = ["entity_type", "entity_id", "action"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = AuditEvent.objects.select_related("actor", "workspace", "organization").all()
        if user.is_superuser:
            workspace_id = self.request.query_params.get("workspace")
            if workspace_id:
                qs = qs.filter(workspace_id=workspace_id)
            return qs
        qs = qs.filter(workspace__memberships__user=user).distinct()
        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        return qs
