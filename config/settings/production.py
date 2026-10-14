"""Production overrides."""

DEBUG = False

if SECRET_KEY in ("", "django-insecure-change-me-in-production"):
    raise RuntimeError("SECRET_KEY must be set to a strong value in production (set via env).")

SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

AUTH_COOKIE_SECURE = True
AUTH_COOKIE_SAMESITE = "Strict"

if ALLOWED_HOSTS in (["*"], []):
    raise RuntimeError("ALLOWED_HOSTS must be set to a concrete list in production.")
