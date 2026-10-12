from rest_framework import serializers

from accounts.models.user import User


class UserOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_email_verified")
        read_only_fields = fields
