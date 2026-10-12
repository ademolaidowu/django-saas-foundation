"""Auth endpoints — thin views that parse input, call services, serialize out."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.cookies import clear_auth_cookie, return_response_with_auth_cookie
from accounts.exceptions import AccountSwitchError, LoginError
from accounts.policies import AccountPolicy
from accounts.selectors import AccountSelectors
from accounts.serializers.input.login import LoginInputSerializer
from accounts.serializers.input.register import RegisterInputSerializer
from accounts.serializers.input.switch import SwitchOrganizationInputSerializer
from accounts.serializers.output.account import AccountOutputSerializer
from accounts.serializers.output.auth import AuthResponseSerializer
from accounts.services import AuthService, RegistrationService
from core.exceptions import APIServiceError


class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = RegisterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, account = RegistrationService.register(**serializer.validated_data)

        response = Response(
            AuthResponseSerializer({"user": user, "account": account}).data,
            status=status.HTTP_201_CREATED,
        )
        return return_response_with_auth_cookie(request=request, response=response, user=user, account=account)


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService.authenticate(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        account = AccountSelectors.get_primary_or_first_active(user)
        if account is None:
            raise APIServiceError(error_code=LoginError.NoActiveAccount)

        response = Response(
            AuthResponseSerializer({"user": user, "account": account}).data,
            status=status.HTTP_200_OK,
        )
        return return_response_with_auth_cookie(request=request, response=response, user=user, account=account)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
        return clear_auth_cookie(response, auth_token=request.auth)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(
            AuthResponseSerializer(
                {"user": request.user, "account": request.account}  # type: ignore[attr-defined]
            ).data
        )


class MyOrganizationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        accounts = AccountSelectors.list_for_user(request.user)  # type: ignore[arg-type]
        return Response(AccountOutputSerializer(accounts, many=True).data)


class SwitchOrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = SwitchOrganizationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = AccountSelectors.get_by_user_and_public_id(
            user=request.user,  # type: ignore[arg-type]
            public_id=serializer.validated_data["account_id"],
        )
        if target is None:
            raise APIServiceError(
                error_code=AccountSwitchError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if not AccountPolicy.can_switch_to(request.user, target):  # type: ignore[arg-type]
            raise APIServiceError(error_code=AccountSwitchError.NotActive)

        # Destroy the old token (cascades its AccountToken) and issue a new one
        # bound to the target account.
        response = Response(
            AuthResponseSerializer({"user": request.user, "account": target}).data,
            status=status.HTTP_200_OK,
        )
        response = clear_auth_cookie(response, auth_token=request.auth)
        return return_response_with_auth_cookie(
            request=request,
            response=response,
            user=request.user,  # type: ignore[arg-type]
            account=target,
        )
