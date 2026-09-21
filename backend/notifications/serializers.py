from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    workspace_slug = serializers.SlugField(source="workspace.slug", read_only=True)

    class Meta:
        model = Notification
        fields = ("id", "workspace", "workspace_slug", "kind", "title", "body",
                  "entity_type", "entity_id", "read", "read_at", "created_at")
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ("id", "kind", "in_app", "email", "updated_at")
        read_only_fields = ("id", "kind", "updated_at")
