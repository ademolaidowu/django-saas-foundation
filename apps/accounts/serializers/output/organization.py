from rest_framework import serializers

from tenants.models.organization import Organization


class OrganizationOutputSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "is_active")
        read_only_fields = fields
