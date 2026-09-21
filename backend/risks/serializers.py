from rest_framework import serializers

from .models import RiskFinding


class RiskFindingSerializer(serializers.ModelSerializer):
    contract_title = serializers.CharField(source="contract.title", read_only=True)
    obligation_title = serializers.CharField(source="obligation.title", read_only=True, default=None)

    class Meta:
        model = RiskFinding
        fields = (
            "id", "workspace", "contract", "contract_title", "obligation", "obligation_title",
            "rule", "points", "severity", "title", "explanation", "evidence", "created_at",
        )
        read_only_fields = fields
