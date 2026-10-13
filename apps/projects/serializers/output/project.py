from rest_framework import serializers

from projects.models.project import Project


class ProjectOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Project
        fields = ("id", "name", "description", "status", "created_at", "modified_at")
        read_only_fields = fields
