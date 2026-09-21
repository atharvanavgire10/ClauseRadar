from rest_framework import serializers

from .models import Obligation


class ObligationSerializer(serializers.ModelSerializer):
    contract_title = serializers.CharField(source="contract.title", read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True, default=None)
    reviewer_email = serializers.EmailField(source="reviewer.email", read_only=True, default=None)

    class Meta:
        model = Obligation
        fields = (
            "id", "workspace", "contract", "contract_title", "document", "clause",
            "page_number", "source_text", "title", "obligation_type", "actor", "action",
            "requirement", "frequency", "evidence_required", "status", "confidence",
            "extraction_method", "owner", "owner_email", "priority", "notes",
            "reviewer", "reviewer_email",
            "reviewed_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "workspace", "contract", "document", "clause", "page_number",
            "source_text", "confidence", "extraction_method", "reviewer",
            "reviewed_at", "created_at", "updated_at",
        )

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()
