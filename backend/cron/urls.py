from django.urls import path

from .views import deadline_scan, recurring_deadlines

urlpatterns = [
    path("recurring-deadlines/", recurring_deadlines, name="cron-recurring-deadlines"),
    path("deadline-scan/", deadline_scan, name="cron-deadline-scan"),
]
