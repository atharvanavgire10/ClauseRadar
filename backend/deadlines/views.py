"""Deadline API — derived statuses, complete/waive/reopen, regenerate."""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import user_can_write_workspace
from .models import Deadline
from .serializers import DeadlineSerializer
from .services import generate_for_contract, set_completed, set_waived


class DeadlineViewSet(viewsets.ModelViewSet):
    serializer_class = DeadlineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "contract", "obligation", "kind", "completed", "waived"]
    search_fields = ["title", "rule"]
    ordering_fields = ["due_date", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Deadline.objects.select_related("contract", "workspace", "obligation").all()
        if not user.is_superuser:
            qs = qs.filter(workspace__memberships__user=user).distinct()
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"),
                             ("obligation", "obligation_id"), ("kind", "kind")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        status_filter = self.request.query_params.get("status")
        if status_filter:
            from datetime import timedelta

            from .engine import today_in_tz

            today = today_in_tz()
            if status_filter == "OVERDUE":
                qs = qs.filter(due_date__lt=today, completed=False, waived=False)
            elif status_filter == "DUE_SOON":
                qs = qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7),
                               completed=False, waived=False)
            elif status_filter == "UPCOMING":
                qs = qs.filter(due_date__gt=today + timedelta(days=7), completed=False, waived=False)
            elif status_filter == "COMPLETED":
                qs = qs.filter(completed=True)
            elif status_filter == "WAIVED":
                qs = qs.filter(waived=True)
        return qs

    def _checked(self, pk) -> Deadline:
        dl = self.get_object()
        if not user_can_write_workspace(self.request.user, dl.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        return dl

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        dl = self._checked(pk)
        return Response(DeadlineSerializer(set_completed(dl.id, actor=request.user, completed=True)).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        dl = self._checked(pk)
        return Response(DeadlineSerializer(set_completed(dl.id, actor=request.user, completed=False)).data)

    @action(detail=True, methods=["post"])
    def waive(self, request, pk=None):
        dl = self._checked(pk)
        return Response(DeadlineSerializer(set_waived(dl.id, actor=request.user, waived=True)).data)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        from contracts.models import Contract

        contract_id = request.data.get("contract")
        if not contract_id:
            return Response({"detail": "contract is required.", "code": "validation_error"}, status=400)
        try:
            contract = Contract.objects.select_related("workspace").get(pk=contract_id)
        except Contract.DoesNotExist:
            return Response({"detail": "Not found.", "code": "not_found"}, status=404)
        if not user_can_write_workspace(request.user, contract.workspace):
            raise PermissionDenied("You do not have write access to this workspace.")
        count = generate_for_contract(contract.id)
        return Response({"contract": str(contract.id), "deadlines": count})
