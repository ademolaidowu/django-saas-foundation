"""
Project-wide exception types.

- `BaseAPIErrorCode`: subclass per app to declare machine-readable error codes.
- `APIServiceError`: service-layer business errors; carries a code + detail;
  rendered by `core.handlers.custom_exception_handler` into the standard
  error envelope.
- `UnscopedQueryError`: raised by `TenantScopedQuerySet` when it is evaluated
  without `.for_organization(org)` or `.unsafe_all()`. See ADR 003.
"""

from __future__ import annotations

from rest_framework import exceptions as drf_exceptions
from rest_framework import status


class BaseAPIErrorCode:
    """Declare `code` and `detail` on a subclass per domain error.

    Example:
        class RoleErrors:
            class NotFound(BaseAPIErrorCode):
                code = "role_0001"
                detail = "Role not found."
    """

    code: str = ""
    detail: str = ""


class APIServiceError(drf_exceptions.APIException):
    """Service-layer business error. Rendered via the custom exception handler."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        error_code: type[BaseAPIErrorCode] | BaseAPIErrorCode,
        detail: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.error_code = error_code
        super().__init__(
            detail=detail or error_code.detail,
            code=error_code.code,
        )
        if status_code is not None:
            self.status_code = status_code  # type: ignore[assignment]


class UnscopedQueryError(RuntimeError):
    """A `TenantScopedQuerySet` was evaluated without `.for_organization(org)`."""
