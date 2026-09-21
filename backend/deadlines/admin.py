from django.contrib import admin

from .models import Deadline


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "due_date", "completed", "waived", "contract")
    list_filter = ("kind", "completed", "waived")
    search_fields = ("title", "rule")
