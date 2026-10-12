from rest_framework import serializers

from accounts.models.account import Account
from accounts.serializers.output.organization import OrganizationOutputSerializer


class AccountOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    organization = OrganizationOutputSerializer(read_only=True)

    class Meta:
        model = Account
        fields = ("id", "organization", "status", "is_primary", "joined_at")
        read_only_fields = fields
