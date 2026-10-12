"""Database configuration. Overridden in test.py for in-memory sqlite."""

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/django_saas_foundation",
    ),
}
