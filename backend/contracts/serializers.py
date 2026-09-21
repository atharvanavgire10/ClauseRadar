from rest_framework import serializers

from .models import Contract, ContractVersion


class ContractSerializer(serializers.ModelSerializer):
    workspace_slug = serializers.SlugField(source="workspace.slug", read_only=True)

    class Meta:
        model = Contract
        fields = (
            "id", "workspace", "workspace_slug", "title", "counterparty",
            "description", "status", "start_date", "end_date", "renewal_date",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from workspaces.models import Workspace

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if request.user.is_superuser:
                self.fields["workspace"].queryset = Workspace.objects.all()
            else:
                self.fields["workspace"].queryset = Workspace.objects.filter(
                    memberships__user=request.user
                ).distinct()

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start is None and self.instance:
            start = self.instance.start_date
        if end is None and self.instance:
            end = self.instance.end_date
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        return attrs


class ContractVersionSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source="document.original_filename", read_only=True, default=None)

    class Meta:
        model = ContractVersion
        fields = ("id", "contract", "version_number", "document", "document_name",
                  "notes", "created_at")
        read_only_fields = fields
