from rest_framework import serializers

from organizations.models import Organization

from .models import Workspace, WorkspaceMembership


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = ("id", "user", "user_email", "role", "created_at")
        read_only_fields = ("id", "created_at")


class WorkspaceSerializer(serializers.ModelSerializer):
    organization_slug = serializers.SlugField(source="organization.slug", read_only=True)
    role = serializers.SerializerMethodField()
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=True)

    class Meta:
        model = Workspace
        fields = (
            "id", "organization", "organization_slug", "name", "slug",
            "workspace_type", "description", "role", "created_at", "updated_at",
        )
        read_only_fields = ("id", "slug", "workspace_type", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if request.user.is_superuser:
                qs = Organization.objects.all()
            else:
                qs = Organization.objects.filter(memberships__user=request.user).distinct()
            self.fields["organization"].queryset = qs

    def get_role(self, obj):
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return None
        try:
            return WorkspaceMembership.objects.get(workspace=obj, user=user).role
        except WorkspaceMembership.DoesNotExist:
            return None
