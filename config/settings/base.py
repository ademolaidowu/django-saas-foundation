"""Core Django settings: apps, middleware, auth, i18n, static."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "drf_spectacular",
    "knox",
    "simple_history",
    # Local
    "core",
    "tenants",
    "accounts",
    "access",
    "projects",
]

AUTH_USER_MODEL = "accounts.User"

# Knox's AuthToken is a swappable model; Django's migration autodetector
# resolves the dependency through this top-level setting.
KNOX_TOKEN_MODEL = "knox.AuthToken"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files inside gunicorn. Must sit immediately
    # after SecurityMiddleware per the project's docs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----------------------------------------------------------------------------
# Auth cookie — overridden per environment in local.py / production.py.
# ----------------------------------------------------------------------------
AUTH_COOKIE_NAME = "auth_token"
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_PATH = "/"
AUTH_COOKIE_SECURE = False
AUTH_COOKIE_SAMESITE = "Lax"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
AUTH_COOKIE_MAX_AGE_REMEMBERED = 60 * 60 * 24 * 30  # 30 days

# ----------------------------------------------------------------------------
# django-simple-history. Reverting is disabled per the project spec; the API
# surface is audit-only. UUID history IDs match our `public_id` discipline.
# ----------------------------------------------------------------------------
SIMPLE_HISTORY_REVERT_DISABLED = True
SIMPLE_HISTORY_HISTORY_ID_USE_UUID = True
SIMPLE_HISTORY_FILEFIELD_TO_CHARFIELD = True

# ----------------------------------------------------------------------------
# Redis cache. Spec says "Redis 7 (cache only for now)" — Django's built-in
# RedisCache backend is enough; no django-redis dep needed.
# ----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    },
}

# ----------------------------------------------------------------------------
# drf-spectacular — OpenAPI schema + Swagger UI.
# ----------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "django-saas-foundation",
    "DESCRIPTION": (
        "A reusable Django SaaS foundation with multi-tenancy, "
        "account-scoped authentication, RBAC, audit trails, and tenant-isolated APIs."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "AccountStatusEnum": "accounts.constants.AccountStatus.choices",
        "RecordSourceEnum": "core.models.base.BaseModel.RecordSource.choices",
    },
}
