"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from core.views import health_view, ready_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health_view, name="health-legacy"),
    path("api/health/", health_view, name="health"),
    path("api/ready/", ready_view, name="ready"),
    path("api/v1/", include("core.urls")),
]
