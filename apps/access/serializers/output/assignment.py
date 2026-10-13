from rest_framework import serializers

from access.models.assignment import RoleAssignment
from access.serializers.output.role import RoleOutputSerializer


class RoleAssignmentOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    account_id = serializers.UUIDField(source="account.public_id", read_only=True)
    role = RoleOutputSerializer(read_only=True)

    class Meta:
        model = RoleAssignment
        fields = ("id", "account_id", "role", "is_active", "created_at")
        read_only_fields = fields
