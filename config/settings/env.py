"""Environment variable parsing. Must be the first include."""

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
