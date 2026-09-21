from django.contrib import admin

from .models import Obligation


@admin.register(Obligation)
class ObligationAdmin(admin.ModelAdmin):
    list_display = ("title", "obligation_type", "status", "actor", "frequency", "contract")
    list_filter = ("status", "obligation_type", "frequency", "extraction_method")
    search_fields = ("title", "actor", "source_text")
