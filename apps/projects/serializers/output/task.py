from rest_framework import serializers

from projects.models.task import Task


class _AssigneeInlineSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)


class _ProjectInlineSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    name = serializers.CharField(read_only=True)


class TaskOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    project = _ProjectInlineSerializer(read_only=True)
    assignee = _AssigneeInlineSerializer(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "project",
            "title",
            "description",
            "status",
            "assignee",
            "due_date",
            "created_at",
            "modified_at",
        )
        read_only_fields = fields
