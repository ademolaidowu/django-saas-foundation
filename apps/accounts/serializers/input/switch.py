from rest_framework import serializers


class SwitchOrganizationInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
