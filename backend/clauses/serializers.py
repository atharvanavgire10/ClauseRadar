from rest_framework import serializers

from .models import Clause


class ClauseSerializer(serializers.ModelSerializer):
    contract_title = serializers.CharField(source="contract.title", read_only=True)
    document_name = serializers.CharField(source="document.original_filename", read_only=True)

    class Meta:
        model = Clause
        fields = (
            "id", "workspace", "contract", "contract_title", "document", "document_name",
            "page", "page_number", "heading", "text", "clause_type",
            "start_offset", "end_offset", "confidence", "extraction_method", "created_at",
        )
        read_only_fields = fields
