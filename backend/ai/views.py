"""AI status + assisted classification endpoints (read-only, rate-limited)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from clauses.detector import classify

from . import service


class BurstThrottle(UserRateThrottle):
    rate = "30/min"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ai_status(request):
    return Response(service.status())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_classify(request):
    text = (request.data.get("text") or "").strip()
    if len(text) < 10:
        return Response({"detail": "text of at least 10 characters is required.", "code": "validation_error"}, status=400)
    rule_type, rule_conf = classify(text)
    ai_result = service.classify_clause_ai(text)
    return Response({
        "rule": {"clause_type": rule_type, "confidence": rule_conf, "method": "RULE"},
        "ai": ({**ai_result, "method": "LLM"} if ai_result else None),
        "used": "LLM" if ai_result else "RULE",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_ask(request):
    from workspaces.models import Workspace

    from .qa import answer

    question = (request.data.get("question") or "").strip()
    if len(question) < 5:
        return Response({"detail": "question of at least 5 characters is required.", "code": "validation_error"}, status=400)
    workspace_id = request.data.get("workspace")
    contract_id = request.data.get("contract")
    workspace = None
    if workspace_id:
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found.", "code": "not_found"}, status=404)
        if not request.user.is_superuser and not workspace.memberships.filter(user=request.user).exists():
            return Response({"detail": "No access to this workspace.", "code": "forbidden"}, status=403)
    elif contract_id:
        from contracts.models import Contract

        try:
            contract = Contract.objects.select_related("workspace").get(pk=contract_id)
        except Contract.DoesNotExist:
            return Response({"detail": "Contract not found.", "code": "not_found"}, status=404)
        workspace = contract.workspace
        if not request.user.is_superuser and not workspace.memberships.filter(user=request.user).exists():
            return Response({"detail": "No access to this workspace.", "code": "forbidden"}, status=403)
    else:
        return Response({"detail": "workspace or contract is required.", "code": "validation_error"}, status=400)
    if contract_id:
        from contracts.models import Contract

        try:
            contract = Contract.objects.get(pk=contract_id, workspace=workspace)
        except Contract.DoesNotExist:
            return Response({"detail": "Contract not found in this workspace.", "code": "not_found"}, status=404)
    return Response(answer(workspace=workspace, question=question, contract_id=contract_id))
