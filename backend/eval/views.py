"""Public evaluation endpoints — no signup, same APIs/business logic, isolated.

Access model: a shared locked-down visitor user scoped by normal workspace
membership to ONLY the eval workspace. All data APIs remain the standard
tenant-scoped viewsets; these endpoints just issue the session and reseed.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status as http_status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .seed import EVAL_PUBLIC_SLUG, VISITOR_EMAIL, seed_eval_workspace


class EvalSessionThrottle(AnonRateThrottle):
    scope = "eval_session"


class EvalResetThrottle(AnonRateThrottle):
    scope = "eval_reset"


def _eval_workspace():
    from workspaces.models import Workspace

    slug = getattr(settings, "PUBLIC_EVAL_SLUG", EVAL_PUBLIC_SLUG)
    return Workspace.objects.filter(workspace_type="PUBLIC_EVAL", public_slug=slug).first()


def _ensure_seeded():
    ws = _eval_workspace()
    if ws is None:
        seed_eval_workspace()
        ws = _eval_workspace()
    return ws


@api_view(["GET"])
@permission_classes([AllowAny])
def eval_info(request):
    ws = _eval_workspace()
    if ws is None:
        return Response({"enabled": getattr(settings, "PUBLIC_EVAL_ENABLED", True),
                         "seeded": False})
    from clauses.models import Clause
    from contracts.models import Contract
    from obligations.models import Obligation

    return Response({
        "enabled": True, "seeded": True,
        "organization": ws.organization.name,
        "contracts": Contract.objects.filter(workspace=ws).count(),
        "clauses": Clause.objects.filter(workspace=ws).count(),
        "obligations": Obligation.objects.filter(workspace=ws).count(),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EvalSessionThrottle])
def eval_session(request):
    if not getattr(settings, "PUBLIC_EVAL_ENABLED", True):
        return Response({"detail": "Evaluation workspace is disabled.", "code": "disabled"}, status=403)
    ws = _ensure_seeded()
    User = get_user_model()
    visitor, _ = User.objects.get_or_create(
        email=VISITOR_EMAIL,
        defaults={"username": VISITOR_EMAIL, "display_name": "Evaluation visitor"})
    if visitor.has_usable_password():
        visitor.set_unusable_password()
        visitor.save()
    from organizations.models import OrganizationMembership
    from workspaces.models import WorkspaceMembership

    OrganizationMembership.objects.get_or_create(
        organization=ws.organization, user=visitor, defaults={"role": "MEMBER"})
    WorkspaceMembership.objects.get_or_create(
        workspace=ws, user=visitor, defaults={"role": "MEMBER"})
    token, _ = Token.objects.get_or_create(user=visitor)
    from accounts.serializers import UserSerializer

    return Response({"user": UserSerializer(visitor).data, "token": token.key,
                     "workspace": str(ws.id)}, status=http_status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EvalResetThrottle])
def eval_reset(request):
    if not getattr(settings, "PUBLIC_EVAL_ENABLED", True):
        return Response({"detail": "Evaluation workspace is disabled.", "code": "disabled"}, status=403)
    from organizations.models import Organization
    from workspaces.models import Workspace

    slug = getattr(settings, "PUBLIC_EVAL_SLUG", EVAL_PUBLIC_SLUG)
    for ws in Workspace.objects.filter(workspace_type="PUBLIC_EVAL", public_slug=slug):
        for doc in ws.documents.all():
            name = doc.file.name
            if name:
                from django.core.files.storage import default_storage

                if default_storage.exists(name):
                    default_storage.delete(name)
        ws.organization.delete()  # cascades workspace + all eval data
    summary = seed_eval_workspace()
    return Response({"reset": True, **summary})
