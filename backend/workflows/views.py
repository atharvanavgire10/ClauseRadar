"""Operational APIs — comments, evidence upload, tasks (all tenant-scoped)."""
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import log_event
from core.permissions import user_can_access_workspace, user_can_write_workspace
from obligations.models import Obligation

from .models import Comment, Evidence, Task
from .serializers import CommentSerializer, EvidenceSerializer, TaskSerializer
from .validation import sanitize_filename, sniff_evidence


def _workspace_of(obj):
    return obj.workspace


class ScopedMixin:
    def scoped_queryset(self, model):
        user = self.request.user
        qs = model.objects.select_related("workspace").all()
        if not user.is_superuser:
            qs = qs.filter(workspace__memberships__user=user).distinct()
        return qs


class CommentViewSet(ScopedMixin, viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "contract", "obligation"]
    search_fields = ["body"]
    ordering_fields = ["created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = self.scoped_queryset(Comment)
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"),
                             ("obligation", "obligation_id")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        from contracts.models import Contract

        contract = serializer.validated_data.get("contract")
        obligation = serializer.validated_data.get("obligation")
        target_ws = None
        if obligation:
            obligation = Obligation.objects.select_related("workspace").get(pk=obligation.pk)
            target_ws = obligation.workspace
        elif contract:
            contract = Contract.objects.select_related("workspace").get(pk=contract.pk)
            target_ws = contract.workspace
        if target_ws is None or not user_can_write_workspace(self.request.user, target_ws):
            raise PermissionDenied("You do not have write access to this workspace.")
        comment = serializer.save(workspace=target_ws, author=self.request.user,
                                  contract=contract, obligation=obligation)
        log_event(actor=self.request.user, organization=target_ws.organization, workspace=target_ws,
                  entity_type="comment", entity_id=comment.id, action="comment.created",
                  metadata={"obligation": str(obligation.id) if obligation else None,
                            "contract": str(contract.id) if contract else None})

    def _checked(self):
        obj = self.get_object()
        if not user_can_write_workspace(self.request.user, obj.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        return obj

    @transaction.atomic
    def perform_update(self, serializer):
        obj = self._checked()
        if obj.author_id != self.request.user.id and not self.request.user.is_superuser:
            raise PermissionDenied("Only the author may edit this comment.")
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        self._checked()
        if instance.author_id != self.request.user.id and not self.request.user.is_superuser:
            raise PermissionDenied("Only the author may delete this comment.")
        instance.delete()


class EvidenceViewSet(ScopedMixin, viewsets.ModelViewSet):
    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["workspace", "obligation"]
    search_fields = ["original_filename", "note"]
    ordering_fields = ["created_at"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = self.scoped_queryset(Evidence)
        for param, field in (("workspace", "workspace_id"), ("obligation", "obligation_id")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        obligation_id = request.data.get("obligation")
        upload = request.FILES.get("file")
        if not obligation_id:
            return Response({"detail": "obligation is required.", "code": "validation_error"}, status=400)
        if upload is None:
            return Response({"detail": "file is required.", "code": "validation_error"}, status=400)
        try:
            ob = Obligation.objects.select_related("workspace").get(pk=obligation_id)
        except Obligation.DoesNotExist:
            return Response({"detail": "Not found.", "code": "not_found"}, status=404)
        if not user_can_write_workspace(request.user, ob.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        from django.conf import settings as dj_settings

        if upload.size and upload.size > int(getattr(dj_settings, "MAX_UPLOAD_MB", 25)) * 1024 * 1024:
            return Response({"detail": "File too large.", "code": "file_too_large"}, status=400)
        head = upload.read(10)
        upload.seek(0)
        filename = sanitize_filename(getattr(upload, "name", "evidence"))
        mime = sniff_evidence(filename, head)
        if mime is None:
            return Response({"detail": "Unsupported file type (PDF, DOCX, PNG, JPG).", "code": "unsupported_type"}, status=400)
        import hashlib

        h = hashlib.sha256()
        for chunk in upload.chunks():
            h.update(chunk)
        upload.seek(0)
        ev = Evidence(workspace=ob.workspace, obligation=ob, original_filename=filename,
                      mime=mime, size_bytes=upload.size or 0, sha256=h.hexdigest(),
                      note=(request.data.get("note") or "")[:500],
                      uploaded_by=request.user if request.user.is_authenticated else None)
        ev.file.save(f"{ev.id}/{filename}", upload, save=False)
        ev.save()
        log_event(actor=request.user, organization=ob.workspace.organization, workspace=ob.workspace,
                  entity_type="evidence", entity_id=ev.id, action="evidence.added",
                  metadata={"obligation": str(ob.id), "filename": filename})
        return Response(EvidenceSerializer(ev).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        ev = self.get_object()
        if not user_can_write_workspace(request.user, ev.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        name = ev.file.name
        ev.delete()
        if name and default_storage.exists(name):
            default_storage.delete(name)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        ev = self.get_object()
        if not user_can_access_workspace(request.user, ev.workspace):
            raise PermissionDenied("You do not have access to this workspace.")
        if not ev.file or not default_storage.exists(ev.file.name):
            return Response({"detail": "File not found.", "code": "not_found"}, status=404)
        return FileResponse(ev.file.open("rb"), content_type=ev.mime,
                            filename=ev.original_filename, as_attachment=False)


class TaskViewSet(ScopedMixin, viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "contract", "obligation", "status", "assignee"]
    search_fields = ["title"]
    ordering_fields = ["created_at", "due_date"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = self.scoped_queryset(Task)
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"),
                             ("obligation", "obligation_id"), ("status", "status")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        from contracts.models import Contract

        contract = serializer.validated_data.get("contract")
        obligation = serializer.validated_data.get("obligation")
        target_ws = None
        if obligation:
            obligation = Obligation.objects.select_related("workspace").get(pk=obligation.pk)
            target_ws = obligation.workspace
            contract = contract or obligation.contract
        if contract and target_ws is None:
            contract = Contract.objects.select_related("workspace").get(pk=contract.pk)
            target_ws = contract.workspace
        if target_ws is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Task must target a contract or an obligation.")
        if not user_can_write_workspace(self.request.user, target_ws):
            raise PermissionDenied("You do not have write access to this workspace.")
        task = serializer.save(workspace=target_ws, contract=contract, obligation=obligation,
                               created_by=self.request.user)
        log_event(actor=self.request.user, organization=target_ws.organization, workspace=target_ws,
                  entity_type="task", entity_id=task.id, action="task.created",
                  metadata={"title": task.title})

    def _checked(self):
        obj = self.get_object()
        if not user_can_write_workspace(self.request.user, obj.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        return obj

    @transaction.atomic
    def perform_update(self, serializer):
        self._checked()
        task = serializer.save()
        log_event(actor=self.request.user, organization=task.workspace.organization, workspace=task.workspace,
                  entity_type="task", entity_id=task.id, action="task.updated",
                  metadata={"title": task.title, "status": task.status})

    @transaction.atomic
    def perform_destroy(self, instance):
        self._checked()
        instance.delete()
