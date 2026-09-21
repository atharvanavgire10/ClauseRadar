from django.contrib import admin

from .models import Comment, Evidence, Task


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("body", "workspace", "author", "created_at")
    search_fields = ("body",)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "obligation", "mime", "created_at")
    list_filter = ("mime",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "assignee", "due_date")
    list_filter = ("status",)
    search_fields = ("title",)
