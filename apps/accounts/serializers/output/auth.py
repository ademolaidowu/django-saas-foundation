from rest_framework import serializers

from accounts.serializers.output.account import AccountOutputSerializer
from accounts.serializers.output.user import UserOutputSerializer


class AuthResponseSerializer(serializers.Serializer):
    user = UserOutputSerializer(read_only=True)
    account = AccountOutputSerializer(read_only=True)
