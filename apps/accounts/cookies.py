"""
Auth-cookie plumbing.

The two public helpers wrap the token-create and token-destroy flows so
views don't have to think about transport. In cookie mode (web) the raw
token lives only in the HttpOnly `Set-Cookie` header. In header mode
(mobile / local dev) the raw token is included in the response body under
`data.token` for the client to store itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from knox.models import AuthToken
from rest_framework.request import Request
from rest_framework.response import Response

if TYPE_CHECKING:
    from accounts.models.account import Account
    from accounts.models.user import User


def is_mobile_client(request: Request) -> bool:
    """A client is "mobile" if it sends `X-Client-Type: mobile`."""
    return request.headers.get("X-Client-Type", "").lower() == "mobile"


def _use_cookie_transport(request: Request) -> bool:
    """
    Cookies are the production default. Mobile clients get the raw token in
    the body; in `LOCAL` dev we also return it so curl is one command long.
    """
    if is_mobile_client(request):
        return False
    if getattr(settings, "LOCAL", False) and not getattr(settings, "TESTING", False):
        return False
    return True


def return_response_with_auth_cookie(
    *,
    request: Request,
    response: Response,
    user: User,
    account: Account,
    extend_expiry: bool = False,
) -> Response:
    """Issue a token for `account`, attach it to `response`, return it."""
    from accounts.models.token import AccountToken

    auth_token_instance, raw_token = AuthToken.objects.create(user=user)
    AccountToken.objects.create(auth_token=auth_token_instance, account=account)

    max_age = (
        settings.AUTH_COOKIE_MAX_AGE_REMEMBERED  # type: ignore[misc]
        if extend_expiry
        else settings.AUTH_COOKIE_MAX_AGE  # type: ignore[misc]
    )

    if _use_cookie_transport(request):
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,  # type: ignore[misc]
            value=raw_token,
            max_age=max_age,
            path=settings.AUTH_COOKIE_PATH,  # type: ignore[misc]
            secure=settings.AUTH_COOKIE_SECURE,  # type: ignore[misc]
            httponly=settings.AUTH_COOKIE_HTTP_ONLY,  # type: ignore[misc]
            samesite=settings.AUTH_COOKIE_SAMESITE,  # type: ignore[misc]
        )
    else:
        if isinstance(response.data, dict):
            response.data = {**response.data, "token": raw_token}

    return response


def clear_auth_cookie(response: Response, auth_token: AuthToken | None) -> Response:
    """Delete the server-side token (cascades `AccountToken`) and the cookie."""
    if auth_token is not None:
        auth_token.delete()
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,  # type: ignore[misc]
        path=settings.AUTH_COOKIE_PATH,  # type: ignore[misc]
        samesite=settings.AUTH_COOKIE_SAMESITE,  # type: ignore[misc]
    )
    return response
