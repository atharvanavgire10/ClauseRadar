from django.contrib import admin

from .models import RiskFinding


@admin.register(RiskFinding)
class RiskFindingAdmin(admin.ModelAdmin):
    list_display = ("rule", "points", "severity", "contract", "obligation")
    list_filter = ("rule", "severity")
    search_fields = ("title", "explanation")
