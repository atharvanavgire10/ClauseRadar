"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from eval.views import eval_info, eval_reset, eval_session
from rest_framework.routers import DefaultRouter

from ai.views import ai_ask, ai_classify, ai_status
from audit.views import AuditEventViewSet
from clauses.views import ClauseViewSet
from contracts.views import ContractViewSet
from deadlines.views import DeadlineViewSet
from documents.views import DocumentViewSet
from notifications.views import NotificationPreferenceViewSet, NotificationViewSet
from obligations.views import ObligationViewSet
from risks.views import RiskFindingViewSet
from search.views import unified_search
from workflows.views import CommentViewSet, EvidenceViewSet, TaskViewSet
from core.views import api_info_view, health_view, ready_view
from organizations.views import OrganizationViewSet
from workspaces.views import WorkspaceViewSet

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"contracts", ContractViewSet, basename="contract")
router.register(r"documents", DocumentViewSet, basename="document")
router.register(r"clauses", ClauseViewSet, basename="clause")
router.register(r"obligations", ObligationViewSet, basename="obligation")
router.register(r"deadlines", DeadlineViewSet, basename="deadline")
router.register(r"risks", RiskFindingViewSet, basename="risk")
router.register(r"comments", CommentViewSet, basename="comment")
router.register(r"evidence", EvidenceViewSet, basename="evidence")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"notification-prefs", NotificationPreferenceViewSet, basename="notification-pref")
router.register(r"audit", AuditEventViewSet, basename="audit")
router.register(r"organizations", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health_view, name="health-legacy"),
    path("api/health/", health_view, name="health"),
    path("api/ready/", ready_view, name="ready"),
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/search/", unified_search, name="unified-search"),
    path("api/v1/eval/info/", eval_info, name="eval-info"),
    path("api/v1/eval/session/", eval_session, name="eval-session"),
    path("api/v1/eval/reset/", eval_reset, name="eval-reset"),
    path("api/v1/ai/status/", ai_status, name="ai-status"),
    path("api/v1/ai/classify/", ai_classify, name="ai-classify"),
    path("api/v1/ai/ask/", ai_ask, name="ai-ask"),
    path("api/v1/", include(router.urls)),
]
