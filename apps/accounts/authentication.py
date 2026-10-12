"""
`AccountTokenAuthentication` — the single auth class for the API.

Resolves `request.user`, `request.account`, and `request.organization` from
whichever token the client presented (cookie first, then Authorization header).
The chain `AuthToken → AccountToken → Account → Organization` is loaded in
one query via `select_related`.

A token is *account-scoped*, not user-scoped: the organization it acts on is
baked into the token at creation and cannot be re-aimed by the client. See
ADR 002.
"""

from __future__ import annotations

from binascii import Error as BinasciiError
from hmac import compare_digest
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from knox.auth import TokenAuthentication
from knox.crypto import hash_token
from knox.models import get_token_model
from knox.settings import CONSTANTS
from rest_framework import exceptions
from rest_framework.request import Request

from accounts.constants import AccountStatus
from accounts.cookies import is_mobile_client

if TYPE_CHECKING:
    from knox.models import AuthToken

    from accounts.models.user import User


class AccountTokenAuthentication(TokenAuthentication):
    """Knox-based auth that attaches account + org context to every request."""

    def authenticate(self, request: Request) -> tuple[User, Any] | None:  # type: ignore[override]
        if is_mobile_client(request) or getattr(settings, "LOCAL", False):
            result = super().authenticate(request)
        else:
            raw_cookie = request.COOKIES.get(settings.AUTH_COOKIE_NAME)  # type: ignore[misc]
            if raw_cookie is None:
                # Fall back to header auth so the Django admin and curl work.
                result = super().authenticate(request)
            else:
                result = self.authenticate_credentials(raw_cookie.encode("utf-8"))

        if result is None:
            return None

        _user, auth_token = result
        self._attach_request_context(request, auth_token)
        return result

    def authenticate_credentials(self, token: bytes) -> tuple[User, AuthToken]:
        """Eagerly join user + account_context + account + organization."""
        msg = _("Invalid token.")
        raw = token.decode("utf-8") if isinstance(token, bytes | bytearray) else token

        qs = (
            get_token_model()
            .objects.filter(token_key=raw[: CONSTANTS.TOKEN_KEY_LENGTH])
            .select_related(
                "user",
                "account_context__account__organization",
            )
        )

        for auth_token in qs:
            if self._cleanup_token(auth_token):
                continue
            try:
                digest = hash_token(raw)
            except (TypeError, BinasciiError):
                raise exceptions.AuthenticationFailed(msg)
            if compare_digest(digest, auth_token.digest):
                return self.validate_user(auth_token)

        raise exceptions.AuthenticationFailed(msg)

    def _attach_request_context(self, request: Request, auth_token: Any) -> None:
        try:
            account = auth_token.account_context.account  # type: ignore[attr-defined]
        except Exception:
            raise exceptions.AuthenticationFailed(_("Token is not scoped to any account. Please log in again."))

        if account.status != AccountStatus.ACTIVE:
            raise exceptions.AuthenticationFailed(_("This account is not active."))

        request.account = account  # type: ignore[attr-defined]
        request.organization = account.organization  # type: ignore[attr-defined]
