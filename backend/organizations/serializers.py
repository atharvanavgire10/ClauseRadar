from rest_framework import serializers

from .models import Organization, OrganizationMembership


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ("id", "user", "user_email", "role", "created_at")
        read_only_fields = ("id", "created_at")


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    members = OrganizationMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "role", "members", "created_at", "updated_at")
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_role(self, obj):
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return None
        try:
            return OrganizationMembership.objects.get(organization=obj, user=user).role
        except OrganizationMembership.DoesNotExist:
            return None
