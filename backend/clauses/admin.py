from django.contrib import admin

from .models import Clause


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = ("clause_type", "document", "page_number", "confidence", "extraction_method")
    list_filter = ("clause_type", "extraction_method")
    search_fields = ("heading", "text")
