"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from audit.views import AuditEventViewSet
from clauses.views import ClauseViewSet
from contracts.views import ContractViewSet
from documents.views import DocumentViewSet
from obligations.views import ObligationViewSet
from core.views import api_info_view, health_view, ready_view
from organizations.views import OrganizationViewSet
from workspaces.views import WorkspaceViewSet

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"contracts", ContractViewSet, basename="contract")
router.register(r"documents", DocumentViewSet, basename="document")
router.register(r"clauses", ClauseViewSet, basename="clause")
router.register(r"obligations", ObligationViewSet, basename="obligation")
router.register(r"audit", AuditEventViewSet, basename="audit")
router.register(r"organizations", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health_view, name="health-legacy"),
    path("api/health/", health_view, name="health"),
    path("api/ready/", ready_view, name="ready"),
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include(router.urls)),
]
