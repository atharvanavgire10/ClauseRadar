"""Document upload / processing / page / download API."""
from __future__ import annotations

from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import log_event
from contracts.models import Contract
from core.permissions import user_can_access_workspace, user_can_write_workspace
from workspaces.models import Workspace

from .extraction import compute_sha256, max_upload_bytes, sanitize_filename, sniff_mime
from .models import Document
from .serializers import DocumentPageSerializer, DocumentSerializer
from .services import process_document


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["workspace", "contract", "status", "mime"]
    search_fields = ["original_filename"]
    ordering_fields = ["created_at", "size_bytes", "page_count"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Document.objects.select_related("workspace", "contract", "workspace__organization").all()
        if not user.is_superuser:
            qs = qs.filter(workspace__memberships__user=user).distinct()
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"), ("status", "status")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    def _contract_for_upload(self, contract_id: str) -> tuple[Contract, Workspace]:
        contract = get_object_or_404(Contract.objects.select_related("workspace"), pk=contract_id)
        workspace = contract.workspace
        if not user_can_write_workspace(self.request.user, workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        return contract, workspace

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        contract_id = request.data.get("contract")
        upload = request.FILES.get("file")
        if not contract_id:
            return Response({"detail": "contract is required.", "code": "validation_error"}, status=400)
        if upload is None:
            return Response({"detail": "file is required.", "code": "validation_error"}, status=400)
        contract, workspace = self._contract_for_upload(contract_id)

        if workspace.workspace_type == "PUBLIC_EVAL":
            from .models import Document as _Doc

            if _Doc.objects.filter(workspace=workspace).count() >= 30:
                return Response(
                    {"detail": "Evaluation workspace upload limit reached (30). Reset to start over.",
                     "code": "eval_limit"},
                    status=429,
                )

        if upload.size and upload.size > max_upload_bytes():
            return Response(
                {"detail": f"File too large (max {max_upload_bytes() // (1024*1024)} MB).", "code": "file_too_large"},
                status=400,
            )
        head = upload.read(8)
        upload.seek(0)
        filename = sanitize_filename(getattr(upload, "name", "upload"))
        mime = sniff_mime(filename, head, getattr(upload, "content_type", ""))
        if mime is None:
            return Response(
                {"detail": "Unsupported file type. Upload a PDF or DOCX file.", "code": "unsupported_type"},
                status=400,
            )
        sha256 = compute_sha256(upload.chunks())
        upload.seek(0)
        existing = Document.objects.filter(workspace=workspace, sha256=sha256).first()
        if existing is not None:
            return Response(
                {
                    "detail": "Duplicate file: identical content already exists in this workspace.",
                    "code": "duplicate",
                    "existing_id": str(existing.id),
                },
                status=409,
            )
        doc = Document(
            workspace=workspace,
            contract=contract,
            original_filename=filename,
            mime=mime,
            size_bytes=upload.size or 0,
            sha256=sha256,
            status=Document.Status.UPLOADED,
            created_by=request.user if request.user.is_authenticated else None,
        )
        doc.file.save(f"{doc.id}/{filename}", upload, save=False)
        doc.save()
        log_event(
            actor=request.user, organization=workspace.organization, workspace=workspace,
            entity_type="document", entity_id=doc.id, action="document.uploaded",
            metadata={"filename": filename, "mime": mime, "size": doc.size_bytes, "contract": str(contract.id)},
        )
        # Process now: eager inline when no worker, background task otherwise.
        from django.conf import settings as dj_settings

        if getattr(dj_settings, "CELERY_TASK_ALWAYS_EAGER", True):
            process_document(doc.id)
        else:
            from .tasks import process_document_task

            process_document_task.delay(str(doc.id))
        doc.refresh_from_db()
        try:
            from contracts.versions import ensure_version_for_document

            ensure_version_for_document(doc.id)
            doc.refresh_from_db()
        except Exception:  # pragma: no cover - versioning must never break upload
            pass
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        doc = self.get_object()
        if not user_can_write_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        name = doc.file.name
        doc_id, workspace, organization = str(doc.id), doc.workspace, doc.workspace.organization
        doc.delete()
        if name and default_storage.exists(name):
            default_storage.delete(name)
        log_event(
            actor=request.user, organization=organization, workspace=workspace,
            entity_type="document", entity_id=doc_id, action="document.deleted", metadata={},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def pages(self, request, pk=None):
        doc = self.get_object()
        if not user_can_access_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have access to this workspace.")
        pages = doc.pages.order_by("page_number").all()
        page = self.paginate_queryset(pages)
        if page is not None:
            return self.get_paginated_response(DocumentPageSerializer(page, many=True).data)
        return Response(DocumentPageSerializer(pages, many=True).data)

    @action(detail=True, methods=["post"], url_path="reprocess")
    def reprocess(self, request, pk=None):
        doc = self.get_object()
        if not user_can_write_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        doc = process_document(doc.id, force=True)
        return Response(DocumentSerializer(doc).data)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        doc = self.get_object()
        if not user_can_access_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have access to this workspace.")
        if not doc.file or not default_storage.exists(doc.file.name):
            return Response({"detail": "File not found.", "code": "not_found"}, status=404)
        return FileResponse(
            doc.file.open("rb"),
            content_type=doc.mime,
            filename=doc.original_filename,
            as_attachment=False,
        )
