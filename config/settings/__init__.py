"""
Settings entry point.

Uses `django-split-settings` to compose a Django settings module from several
files. The sequence is:

    env.py       → environment variable parsing and SECRET_KEY
    base.py      → INSTALLED_APPS, MIDDLEWARE, AUTH, TIME_ZONE, etc.
    database.py  → DATABASES
    drf.py       → REST_FRAMEWORK (pagination, exception handler, renderer)
    tenancy.py   → TENANT_GUARD_ENABLED, TENANT_GUARD_MODE
    <profile>.py → local.py | test.py | production.py (one, picked by env)

Each file receives the globals from earlier files via split_settings, so e.g.
`drf.py` can read values set in `base.py`.
"""

import os
import sys
from pathlib import Path

import environ
from split_settings.tools import include

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_apps_dir = str(BASE_DIR / "apps")
if _apps_dir not in sys.path:
    sys.path.insert(0, _apps_dir)

env = environ.Env(
    TESTING=(bool, False),
    LOCAL=(bool, False),
    PROD=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.is_file():
    env.read_env(str(env_file))

CURRENT_DJANGO_COMMAND = sys.argv[1] if len(sys.argv) > 1 else ""

TESTING = env("TESTING") or CURRENT_DJANGO_COMMAND in ("test", "pytest")
LOCAL = env("LOCAL")
PROD = env("PROD")

if int(TESTING) + int(LOCAL) + int(PROD) > 1:
    raise RuntimeError(
        f"Set exactly one of TESTING / LOCAL / PROD. Got TESTING={TESTING}, LOCAL={LOCAL}, PROD={PROD}."
    )

if TESTING:
    _profile = "test.py"
elif PROD:
    _profile = "production.py"
else:
    _profile = "local.py"

include(
    "env.py",
    "base.py",
    "database.py",
    "drf.py",
    "tenancy.py",
    _profile,
)
