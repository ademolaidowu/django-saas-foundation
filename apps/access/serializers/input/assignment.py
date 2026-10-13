from rest_framework import serializers


class RoleAssignmentCreateInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    role_id = serializers.UUIDField()
