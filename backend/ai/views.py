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
