"""Django REST Framework + Knox configuration."""

from datetime import timedelta

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "core.renderers.EnvelopeJSONRenderer",
    ],
    "EXCEPTION_HANDLER": "core.handlers.custom_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.AccountTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

REST_KNOX = {
    "SECURE_HASH_ALGORITHM": "hashlib.sha512",
    "AUTH_TOKEN_CHARACTER_LENGTH": 64,
    "TOKEN_TTL": timedelta(days=7),
    "USER_SERIALIZER": None,
    "TOKEN_LIMIT_PER_USER": None,
    "AUTO_REFRESH": False,
}
