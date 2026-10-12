"""
Custom DRF exception handler — produces a consistent error envelope.

Response shape:
    {
        "error": {
            "code": "role_0001",
            "message": "Role not found.",
            "request_id": "...",
            "fields": {...}    # only on ValidationError
        }
    }

Wire up in settings:
    REST_FRAMEWORK = {"EXCEPTION_HANDLER": "core.handlers.custom_exception_handler"}
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.exceptions import APIServiceError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception", exc_info=exc)
        return Response(
            _build_error_response(
                code="internal_error",
                message="An internal error occurred.",
                request_id=_get_request_id(context),
            ),
            status=500,
        )

    response.data = _build_error_response(
        code=_get_error_code(exc),
        message=_get_error_message(exc),
        request_id=_get_request_id(context),
        fields=_get_field_errors(exc),
    )
    return response


def _build_error_response(
    code: str,
    message: str,
    request_id: str,
    fields: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if fields:
        error["fields"] = fields
    return {"error": error}


_CODE_MAP: dict[type[Exception], str] = {
    exceptions.ValidationError: "validation_error",
    exceptions.ParseError: "invalid_request",
    exceptions.AuthenticationFailed: "authentication_failed",
    exceptions.NotAuthenticated: "authentication_required",
    exceptions.PermissionDenied: "permission_denied",
    DjangoPermissionDenied: "permission_denied",
    exceptions.NotFound: "not_found",
    Http404: "not_found",
    exceptions.MethodNotAllowed: "method_not_allowed",
    exceptions.NotAcceptable: "not_acceptable",
    exceptions.UnsupportedMediaType: "unsupported_media_type",
    exceptions.Throttled: "rate_limited",
}


def _get_error_code(exc: Exception) -> str:
    if isinstance(exc, APIServiceError) and getattr(exc, "error_code", None) is not None:
        return exc.error_code.code
    if hasattr(exc, "code") and exc.code:
        return str(exc.code)
    if hasattr(exc, "default_code"):
        return str(exc.default_code)
    for exc_class, code in _CODE_MAP.items():
        if isinstance(exc, exc_class):
            return code
    return "internal_error"


def _get_error_message(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        return str(detail[0])
    if isinstance(detail, dict):
        if "detail" in detail:
            return str(detail["detail"])
        if "non_field_errors" in detail:
            errors = detail["non_field_errors"]
            return str(errors[0]) if errors else "Validation error."
        return "Validation error."
    return str(exc) or "An error occurred."


def _get_field_errors(exc: Exception) -> dict[str, list[str]] | None:
    if not isinstance(exc, exceptions.ValidationError):
        return None
    if not isinstance(exc.detail, dict):
        return None

    fields: dict[str, list[str]] = {}
    for field, errors in exc.detail.items():
        if field in ("detail", "non_field_errors"):
            continue
        if isinstance(errors, list):
            fields[field] = [str(e) for e in errors]
        else:
            fields[field] = [str(errors)]
    return fields or None


def _get_request_id(context: dict[str, Any]) -> str:
    request = context.get("request")
    if request is not None and hasattr(request, "request_id"):
        return str(request.request_id)
    return str(uuid.uuid4())
