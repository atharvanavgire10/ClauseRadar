from django.contrib import admin

from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("kind", "user", "title", "read", "email_sent", "created_at")
    list_filter = ("kind", "read", "email_sent")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "in_app", "email")
    list_filter = ("kind",)
