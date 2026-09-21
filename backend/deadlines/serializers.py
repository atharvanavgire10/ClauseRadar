from rest_framework import serializers

from .engine import deadline_status, today_in_tz
from .models import Deadline


class DeadlineSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    contract_title = serializers.CharField(source="contract.title", read_only=True)
    obligation_title = serializers.CharField(source="obligation.title", read_only=True, default=None)

    class Meta:
        model = Deadline
        fields = (
            "id", "workspace", "contract", "contract_title", "obligation", "obligation_title",
            "title", "kind", "due_date", "anchor_date", "offset_days", "business_days",
            "rule", "status", "completed", "waived", "completed_at", "created_at",
        )
        read_only_fields = (
            "id", "workspace", "contract", "obligation", "title", "kind", "due_date",
            "anchor_date", "offset_days", "business_days", "rule", "status",
            "completed_at", "created_at",
        )

    def get_status(self, obj):
        return deadline_status(obj.due_date, today_in_tz(), completed=obj.completed, waived=obj.waived)
