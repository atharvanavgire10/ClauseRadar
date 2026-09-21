from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditEvent
        fields = (
            "id", "actor", "actor_email", "organization", "workspace",
            "entity_type", "entity_id", "action", "metadata", "created_at",
        )
        read_only_fields = fields
