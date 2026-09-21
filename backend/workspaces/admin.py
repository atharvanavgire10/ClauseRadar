from django.contrib import admin

from .models import Workspace, WorkspaceMembership


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "workspace_type", "created_at")
    list_filter = ("workspace_type",)
    search_fields = ("name", "slug")


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "created_at")
    list_filter = ("role",)
