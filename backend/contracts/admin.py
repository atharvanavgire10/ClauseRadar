from django.contrib import admin

from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("title", "workspace", "status", "counterparty", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "counterparty")
