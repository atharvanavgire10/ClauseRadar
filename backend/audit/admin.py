from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "workspace", "actor", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "action")
    readonly_fields = ("id", "actor", "organization", "workspace", "entity_type", "entity_id", "action", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
