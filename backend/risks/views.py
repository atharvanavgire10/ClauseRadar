"""Risk API — read findings, per-contract score summary, trigger assessment."""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import user_can_access_workspace, user_can_write_workspace
from .models import RiskFinding
from .serializers import RiskFindingSerializer
from .services import assess_contract_risks


class RiskFindingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RiskFindingSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workspace", "contract", "obligation", "rule", "severity"]
    search_fields = ["title", "explanation", "rule"]
    ordering_fields = ["points", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = RiskFinding.objects.select_related("contract", "workspace", "obligation").all()
        if not user.is_superuser:
            qs = qs.filter(workspace__memberships__user=user).distinct()
        for param, field in (("workspace", "workspace_id"), ("contract", "contract_id"),
                             ("obligation", "obligation_id"), ("rule", "rule"),
                             ("severity", "severity")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        from contracts.models import Contract

        contract_id = request.query_params.get("contract")
        if not contract_id:
            return Response({"detail": "contract query param is required.", "code": "validation_error"}, status=400)
        try:
            contract = Contract.objects.select_related("workspace").get(pk=contract_id)
        except Contract.DoesNotExist:
            return Response({"detail": "Not found.", "code": "not_found"}, status=404)
        if not user_can_access_workspace(request.user, contract.workspace):
            raise PermissionDenied("You do not have access to this workspace.")
        findings = self.get_queryset().filter(contract=contract)
        score = min(100, sum(f.points for f in findings))
        from .rules import level_for

        return Response({
            "contract": str(contract.id), "score": score, "level": level_for(score),
            "findings": RiskFindingSerializer(findings, many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="assess")
    def assess(self, request):
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
        result = assess_contract_risks(contract.id)
        return Response({
            "contract": str(contract.id), "score": result["score"], "level": result["level"],
            "findings": RiskFindingSerializer(result["findings"], many=True).data,
        })
