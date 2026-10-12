from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class RegisterInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    organization_name = serializers.CharField(max_length=200)
    organization_slug = serializers.SlugField(max_length=100)

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value
