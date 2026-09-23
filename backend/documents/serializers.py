from rest_framework import serializers

from .models import Document, DocumentPage


class DocumentSerializer(serializers.ModelSerializer):
    workspace_slug = serializers.SlugField(source="workspace.slug", read_only=True)
    # Opaque storage identifier (local path or Blob reference) — never a
    # directly-fetchable URL. Downloads go through the permission-checked
    # download endpoint, which is what keeps private files private.
    file = serializers.SerializerMethodField()

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

    def get_file(self, obj):
        return obj.file.name if obj.file else None


class DocumentPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentPage
        fields = ("id", "page_number", "text", "char_count")
        read_only_fields = fields
