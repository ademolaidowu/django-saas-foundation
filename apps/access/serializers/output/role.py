from rest_framework import serializers

from access.models.role import Role


class RoleOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "code",
            "name",
            "description",
            "is_system",
            "permission_codes",
            "created_at",
        )
        read_only_fields = fields

    def get_permission_codes(self, obj: Role) -> list[str]:
        return sorted(p.code for p in obj.permissions.all())
