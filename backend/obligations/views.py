"""Obligation API — list/retrieve/create/edit + review workflow."""
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import log_event
from core.permissions import user_can_access_workspace, user_can_write_workspace
from .models import Obligation
from .serializers import ObligationSerializer
from .services import (
    activate_obligation,
    assign_owner,
    complete_obligation,
    confirm_obligation,
    reject_obligation,
    reopen_obligation,
    start_progress,
    waive_obligation,
)


class ObligationViewSet(viewsets.ModelViewSet):
    serializer_class = ObligationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "contract", "document", "obligation_type", "status", "frequency", "owner", "priority"]
    search_fields = ["title", "actor", "action", "requirement", "source_text"]
    ordering_fields = ["created_at", "updated_at", "confidence"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Obligation.objects.select_related("contract", "workspace", "owner", "reviewer").all()
        if not user.is_superuser:
            qs = qs.filter(workspace__memberships__user=user).distinct()
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"),
                             ("status", "status"), ("obligation_type", "obligation_type"),
                             ("owner", "owner_id")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        from contracts.models import Contract

        contract = serializer.validated_data.get("contract")
        if contract is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"contract": "contract is required."})
        try:
            contract = Contract.objects.select_related("workspace").get(pk=contract.pk)
        except Contract.DoesNotExist:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"contract": "Invalid contract."})
        if not user_can_write_workspace(self.request.user, contract.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        ob = serializer.save(workspace=contract.workspace, status=Obligation.Status.NEEDS_REVIEW,
                             extraction_method=Obligation.Method.RULE)
        log_event(
            actor=self.request.user, organization=contract.workspace.organization, workspace=contract.workspace,
            entity_type="obligation", entity_id=ob.id, action="obligation.created",
            metadata={"title": ob.title, "type": ob.obligation_type},
        )

    @transaction.atomic
    def perform_update(self, serializer):
        if not user_can_write_workspace(self.request.user, serializer.instance.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        ob = serializer.save()
        log_event(
            actor=self.request.user, organization=ob.workspace.organization, workspace=ob.workspace,
            entity_type="obligation", entity_id=ob.id, action="obligation.updated",
            metadata={"title": ob.title, "status": ob.status},
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        if not user_can_write_workspace(self.request.user, instance.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        log_event(
            actor=self.request.user, organization=instance.workspace.organization, workspace=instance.workspace,
            entity_type="obligation", entity_id=instance.id, action="obligation.deleted",
            metadata={"title": instance.title},
        )
        instance.delete()

    def _checked(self, pk) -> Obligation:
        ob = self.get_object()
        if not user_can_write_workspace(self.request.user, ob.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        return ob

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = confirm_obligation(ob.id, reviewer=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = reject_obligation(ob.id, reviewer=request.user, reason=request.data.get("reason", ""))
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = activate_obligation(ob.id, actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = start_progress(ob.id, actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = complete_obligation(ob.id, actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = reopen_obligation(ob.id, actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"])
    def waive(self, request, pk=None):
        ob = self._checked(pk)
        try:
            ob = waive_obligation(ob.id, actor=request.user, reason=request.data.get("reason", ""))
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
        return Response(ObligationSerializer(ob).data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        from django.contrib.auth import get_user_model

        from workspaces.models import WorkspaceMembership

        ob = self._checked(pk)
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            try:
                ob = assign_owner(ob.id, actor=request.user, owner=None)
            except ValueError as exc:
                return Response({"detail": str(exc), "code": "invalid_transition"}, status=400)
            return Response(ObligationSerializer(ob).data)
        User = get_user_model()
        try:
            target = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found.", "code": "not_found"}, status=404)
        if not WorkspaceMembership.objects.filter(workspace=ob.workspace, user=target).exists():
            return Response({"detail": "User is not a member of this workspace.", "code": "not_member"}, status=400)
        ob = assign_owner(ob.id, actor=request.user, owner=target)
        return Response(ObligationSerializer(ob).data)

    @action(detail=False, methods=["post"], url_path="extract")
    def extract(self, request):
        from documents.models import Document

        from .services import extract_obligations_for_document

        document_id = request.data.get("document")
        if not document_id:
            return Response({"detail": "document is required.", "code": "validation_error"}, status=400)
        try:
            doc = Document.objects.select_related("workspace").get(pk=document_id)
        except Document.DoesNotExist:
            return Response({"detail": "Not found.", "code": "not_found"}, status=404)
        if not user_can_write_workspace(request.user, doc.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        count = extract_obligations_for_document(doc.id)
        return Response({"document": str(doc.id), "obligations": count}, status=status.HTTP_200_OK)
