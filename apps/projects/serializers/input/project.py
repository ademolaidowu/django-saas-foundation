from rest_framework import serializers

from projects.constants import ProjectStatus


class ProjectCreateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=ProjectStatus.choices,
        required=False,
        default=ProjectStatus.ACTIVE,
    )


class ProjectUpdateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=False)
