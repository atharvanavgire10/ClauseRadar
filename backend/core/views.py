"""Phase 00 public views: health, readiness, API info."""
from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.http import Http404
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_view(request):
    return Response({"status": "ok", "service": "clauseradar-api", "version": "0.0.0"})


@api_view(["GET"])
@permission_classes([AllowAny])
def ready_view(request):
    checks = {"database": "unknown"}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:  # pragma: no cover - surfaced as not-ready
        checks["database"] = "error"
    ok = checks["database"] == "ok"
    return Response(
        {"ready": ok, "checks": checks, "ai_provider": getattr(settings, "AI_PROVIDER", "none")},
        status=200 if ok else 503,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info_view(request):
    return Response(
        {
            "name": "ClauseRadar API",
            "version": "v1",
            "tagline": "From contract clauses to actions.",
            "endpoints": ["/api/health/", "/api/ready/", "/api/v1/"],
        }
    )


def frontend_view(request):
    """Serve the built React SPA entrypoint (Vercel native deployment).

    backend/templates/index.html is produced by frontend/scripts/sync-spa.js
    during the Vercel build. Where it is absent (local dev, Docker — where a
    dedicated static server owns the SPA), fall through to 404 to preserve
    existing behavior.
    """
    try:
        return render(request, "index.html", content_type="text/html")
    except TemplateDoesNotExist:
        raise Http404("Frontend is not built for this deployment.")
