from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import log_event
from core.permissions import user_can_access_workspace, user_can_write_workspace
from .models import Contract, ContractVersion
from .serializers import ContractSerializer, ContractVersionSerializer
from .versions import compare_versions, ensure_versions_for_contract


class ContractViewSet(viewsets.ModelViewSet):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "status", "counterparty"]
    search_fields = ["title", "counterparty", "description"]
    ordering_fields = ["created_at", "updated_at", "title", "renewal_date"]

    def get_queryset(self):
        user = self.request.user
        qs = Contract.objects.select_related("workspace", "workspace__organization").all()
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

    def _check_workspace(self, workspace, write=False):
        if write and not user_can_write_workspace(self.request.user, workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        if not write and not user_can_access_workspace(self.request.user, workspace):
            raise PermissionDenied("You do not have access to this workspace.")

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.validated_data["workspace"]
        self._check_workspace(workspace, write=True)
        contract = serializer.save(created_by=self.request.user)
        log_event(
            actor=self.request.user, organization=workspace.organization, workspace=workspace,
            entity_type="contract", entity_id=contract.id, action="contract.created",
            metadata={"title": contract.title},
        )
        try:
            from deadlines.services import generate_for_contract

            generate_for_contract(contract.id)
        except Exception:  # pragma: no cover - deadlines must never break contracts
            pass

    @transaction.atomic
    def perform_update(self, serializer):
        self._check_workspace(serializer.instance.workspace, write=True)
        contract = serializer.save()
        log_event(
            actor=self.request.user,
            organization=contract.workspace.organization, workspace=contract.workspace,
            entity_type="contract", entity_id=contract.id, action="contract.updated",
            metadata={"title": contract.title, "status": contract.status},
        )
        try:
            from deadlines.services import generate_for_contract

            generate_for_contract(contract.id)
        except Exception:  # pragma: no cover
            pass

    @transaction.atomic
    def perform_destroy(self, instance):
        self._check_workspace(instance.workspace, write=True)
        log_event(
            actor=self.request.user,
            organization=instance.workspace.organization, workspace=instance.workspace,
            entity_type="contract", entity_id=instance.id, action="contract.deleted",
            metadata={"title": instance.title},
        )
        instance.delete()

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        contract = self.get_object()
        ensure_versions_for_contract(contract.id)
        versions = ContractVersion.objects.filter(contract=contract).order_by("version_number")
        return Response(ContractVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"], url_path="compare")
    def compare(self, request, pk=None):
        contract = self.get_object()
        try:
            from_number = int(request.query_params.get("from", ""))
            to_number = int(request.query_params.get("to", ""))
        except (TypeError, ValueError):
            return Response({"detail": "from and to version numbers are required.", "code": "validation_error"}, status=400)
        try:
            result = compare_versions(contract.id, from_number, to_number)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "not_found"}, status=404)
        return Response(result)
