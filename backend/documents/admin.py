from django.contrib import admin

from .models import Document, DocumentPage


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "contract", "status", "page_count", "mime", "created_at")
    list_filter = ("status", "mime")
    search_fields = ("original_filename", "sha256")
    readonly_fields = ("sha256", "size_bytes", "page_count", "processed_at")


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = ("document", "page_number", "char_count")
    list_filter = ("document",)
