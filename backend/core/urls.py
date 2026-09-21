from django.urls import path

from .views import api_info_view

urlpatterns = [
    path("", api_info_view, name="api-info"),
]
