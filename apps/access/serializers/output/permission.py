from rest_framework import serializers

from access.models.permission import Permission


class PermissionOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Permission
        fields = ("id", "code", "module", "description")
        read_only_fields = fields
