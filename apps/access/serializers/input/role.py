from rest_framework import serializers


class RoleCreateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )


class RoleUpdateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
    )
