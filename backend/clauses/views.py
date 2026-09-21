"""Read-only clause API + manual re-extract action."""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import user_can_access_workspace, user_can_write_workspace
from .models import Clause
from .serializers import ClauseSerializer


class ClauseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ClauseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "contract", "document", "clause_type", "page_number"]
    search_fields = ["heading", "text"]
    ordering_fields = ["created_at", "page_number", "confidence"]

    def get_queryset(self):
        user = self.request.user
        qs = Clause.objects.select_related("contract", "document", "page", "workspace").all()
        if not user.is_superuser:
            qs = qs.filter(workspace__memberships__user=user).distinct()
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"),
                             ("document", "document_id"), ("clause_type", "clause_type")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    @action(detail=False, methods=["post"], url_path="extract")
    def extract(self, request):
        """Trigger (re)extraction for a document: {document: <uuid>}."""
        from documents.models import Document

        from .services import extract_clauses_for_document

        document_id = request.data.get("document")
        if not document_id:
            return Response({"detail": "document is required.", "code": "validation_error"}, status=400)
        try:
            doc = Document.objects.select_related("workspace").get(pk=document_id)
        except Document.DoesNotExist:
            return Response({"detail": "Not found.", "code": "not_found"}, status=404)
        if not user_can_access_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have access to this workspace.")
        if not user_can_write_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        count = extract_clauses_for_document(doc.id)
        return Response({"document": str(doc.id), "clauses": count})
