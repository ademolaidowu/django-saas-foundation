"""
Direct tests of `core.handlers.custom_exception_handler`.

Each DRF / Django exception type should produce the standard
`{"error": {"code", "message", "request_id", "fields?"}}` envelope with the
appropriate HTTP status.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from core.exceptions import APIServiceError, BaseAPIErrorCode
from core.handlers import custom_exception_handler


class _MyCode(BaseAPIErrorCode):
    code = "test_1234"
    detail = "test detail"


def _context():
    return {"request": APIRequestFactory().get("/")}


class TestCustomExceptionHandler:
    def test_api_service_error_uses_code(self):
        exc = APIServiceError(error_code=_MyCode)
        response = custom_exception_handler(exc, _context())
        assert response is not None
        assert response.data["error"]["code"] == "test_1234"
        assert response.data["error"]["message"] == "test detail"
        assert "request_id" in response.data["error"]

    def test_api_service_error_with_custom_status(self):
        exc = APIServiceError(error_code=_MyCode, status_code=418)
        response = custom_exception_handler(exc, _context())
        assert response is not None
        assert response.status_code == 418

    def test_validation_error_dict_produces_fields(self):
        exc = exceptions.ValidationError({"email": ["invalid"]})
        response = custom_exception_handler(exc, _context())
        # Field errors are surfaced; DRF's inner `code` wins when set.
        assert response.data["error"]["fields"] == {"email": ["invalid"]}
        assert response.status_code == 400

    def test_validation_error_with_non_field_errors(self):
        exc = exceptions.ValidationError({"non_field_errors": ["bad combination"]})
        response = custom_exception_handler(exc, _context())
        assert response.data["error"]["message"] == "bad combination"
        # non_field_errors is excluded from field-level dict
        assert "fields" not in response.data["error"]

    def test_validation_error_list_summary_message(self):
        exc = exceptions.ValidationError(["something went wrong"])
        response = custom_exception_handler(exc, _context())
        assert response.data["error"]["message"] == "something went wrong"

    def test_validation_error_string(self):
        exc = exceptions.ValidationError("terse")
        response = custom_exception_handler(exc, _context())
        assert response.data["error"]["message"] == "terse"

    @pytest.mark.parametrize(
        ("exc_cls", "expected_status"),
        [
            (exceptions.AuthenticationFailed, 401),
            (exceptions.NotAuthenticated, 401),
            (exceptions.PermissionDenied, 403),
            (exceptions.NotFound, 404),
            (exceptions.MethodNotAllowed, 405),
            (exceptions.NotAcceptable, 406),
            (exceptions.UnsupportedMediaType, 415),
            (exceptions.ParseError, 400),
        ],
    )
    def test_drf_exceptions_mapped_to_envelope(self, exc_cls, expected_status):
        """Every DRF exception type produces the standard envelope at the right status."""
        kwargs: dict = {}
        if exc_cls is exceptions.MethodNotAllowed:
            kwargs["method"] = "POST"
        elif exc_cls is exceptions.UnsupportedMediaType:
            kwargs["media_type"] = "application/xml"
        exc = exc_cls(**kwargs)
        response = custom_exception_handler(exc, _context())
        assert response.status_code == expected_status
        error = response.data["error"]
        assert "code" in error
        assert "message" in error
        assert "request_id" in error

    def test_django_http404(self):
        response = custom_exception_handler(Http404("gone"), _context())
        assert response.data["error"]["code"] == "not_found"

    def test_django_permission_denied(self):
        response = custom_exception_handler(DjangoPermissionDenied("nope"), _context())
        assert response.data["error"]["code"] == "permission_denied"

    def test_unhandled_exception_becomes_500(self):
        response = custom_exception_handler(RuntimeError("boom"), _context())
        assert response is not None
        assert response.status_code == 500
        assert response.data["error"]["code"] == "internal_error"

    def test_request_id_from_request_attr(self):
        req = APIRequestFactory().get("/")
        req.request_id = "fixed-id"
        response = custom_exception_handler(APIServiceError(error_code=_MyCode), {"request": req})
        assert response.data["error"]["request_id"] == "fixed-id"

    def test_request_id_falls_back_to_uuid_when_no_request(self):
        response = custom_exception_handler(APIServiceError(error_code=_MyCode), {})
        # Just needs to be a non-empty string
        assert isinstance(response.data["error"]["request_id"], str)
        assert len(response.data["error"]["request_id"]) > 0
