"""
`@require_permission("code")` — the gate on every protected view.

Single-permission form only. To require two codes, stack decorators. To
express OR, do the check inline — a second decorator-level feature is more
API than the pattern needs right now.

The decorator looks for `request.account` on the DRF request; the auth
class (`accounts.authentication.AccountTokenAuthentication`) sets that on
every authenticated request. If the account isn't present, we treat it as
a denial (403) — the view's permission_classes would also reject, but the
decorator should be safe even when stacked under a mis-configured view.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from rest_framework import status
from rest_framework.request import Request

from access.exceptions import PermissionDenied
from access.selectors import PermissionSelectors
from core.exceptions import APIServiceError


def _resolve_request(args: tuple[Any, ...]) -> Request | None:
    """Return the DRF `Request` from either `(self, request, ...)` or `(request, ...)`."""
    for arg in args[:2]:
        if isinstance(arg, Request):
            return arg
    return None


def require_permission(code: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view_fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _resolve_request(args)
            account = getattr(request, "account", None) if request is not None else None
            if account is None or not PermissionSelectors.account_has_permission(account, code):
                raise APIServiceError(
                    error_code=PermissionDenied,
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            return view_fn(*args, **kwargs)

        return wrapper

    return decorator
