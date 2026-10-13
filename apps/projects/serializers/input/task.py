from rest_framework import serializers

from projects.constants import TaskStatus


class TaskCreateInputSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=TaskStatus.choices,
        required=False,
        default=TaskStatus.TODO,
    )
    assignee_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    due_date = serializers.DateField(required=False, allow_null=True, default=None)


class TaskUpdateInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
