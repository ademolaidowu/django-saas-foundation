from rest_framework import serializers


class LoginInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)
