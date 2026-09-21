"""Unified search endpoint — same shape on PostgreSQL and SQLite."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services import SEARCHABLE_TYPES, search_workspace


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unified_search(request):
    query = request.query_params.get("q", "")
    types = [t.strip() for t in (request.query_params.get("types") or "").split(",") if t.strip()]
    risk_min = request.query_params.get("risk_min")
    try:
        result = search_workspace(
            user=request.user,
            query=query,
            types=types or None,
            workspace_id=request.query_params.get("workspace") or None,
            contract_id=request.query_params.get("contract") or None,
            obligation_type=request.query_params.get("obligation_type") or None,
            risk_min=int(risk_min) if risk_min else None,
            date_from=request.query_params.get("date_from") or None,
            date_to=request.query_params.get("date_to") or None,
            limit=min(int(request.query_params.get("limit", 50)), 100),
        )
    except ValueError as exc:
        return Response({"detail": str(exc), "code": "validation_error"}, status=400)
    return Response({**result, "searchable_types": list(SEARCHABLE_TYPES)})
