from rest_framework import serializers

from .models import Document, DocumentPage


class DocumentSerializer(serializers.ModelSerializer):
    workspace_slug = serializers.SlugField(source="workspace.slug", read_only=True)

    class Meta:
        model = Document
        fields = (
            "id", "workspace", "workspace_slug", "contract", "file", "original_filename",
            "mime", "size_bytes", "sha256", "status", "page_count", "error_message",
            "ocr_used", "processed_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "workspace", "file", "original_filename", "mime", "size_bytes",
            "sha256", "status", "page_count", "error_message", "ocr_used",
            "processed_at", "created_at", "updated_at",
        )


class DocumentPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentPage
        fields = ("id", "page_number", "text", "char_count")
        read_only_fields = fields
