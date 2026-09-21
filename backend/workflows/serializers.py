from rest_framework import serializers

from .models import Comment, Evidence, Task


class CommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True, default=None)

    class Meta:
        model = Comment
        fields = ("id", "workspace", "contract", "obligation", "author", "author_email",
                  "body", "created_at", "updated_at")
        read_only_fields = ("id", "workspace", "author", "created_at", "updated_at")

    def validate(self, attrs):
        contract = attrs.get("contract") or getattr(self.instance, "contract", None)
        obligation = attrs.get("obligation") or getattr(self.instance, "obligation", None)
        if not contract and not obligation:
            raise serializers.ValidationError("Comment must target a contract or an obligation.")
        if not attrs.get("body", "").strip():
            raise serializers.ValidationError({"body": "Comment body is required."})
        return attrs


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True, default=None)
    # Opaque storage identifier — see DocumentSerializer. Downloads go through
    # the permission-checked download endpoint.
    file = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = ("id", "workspace", "obligation", "file", "original_filename", "mime",
                  "size_bytes", "sha256", "note", "uploaded_by", "uploaded_by_email", "created_at")
        read_only_fields = ("id", "workspace", "file", "original_filename", "mime",
                            "size_bytes", "sha256", "uploaded_by", "created_at")

    def get_file(self, obj):
        return obj.file.name if obj.file else None


class TaskSerializer(serializers.ModelSerializer):
    assignee_email = serializers.EmailField(source="assignee.email", read_only=True, default=None)

    class Meta:
        model = Task
        fields = ("id", "workspace", "contract", "obligation", "title", "status",
                  "assignee", "assignee_email", "due_date", "created_at", "updated_at")
        read_only_fields = ("id", "workspace", "created_at", "updated_at")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()
