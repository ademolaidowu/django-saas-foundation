"""
Shared pytest fixtures for every test suite.

- `two_orgs`, `widget_model`: tenancy harness (Phase 1).
- `api_client`, `password`, `user_factory`, `account_factory`, `authed_client`:
   identity harness (Phase 2). Promoted from `tests/accounts/conftest.py` so
   downstream apps (`tests/access/`, future `tests/projects/`) can reuse them.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import connection, models
from rest_framework.test import APIClient

from accounts.constants import AccountStatus
from accounts.models.account import Account
from accounts.models.user import User
from core.models.tenancy import TenantScopedModel
from tenants.models.organization import Organization

PASSWORD = "testpassword123"


@pytest.fixture(autouse=True)
def _seed_permissions(db):
    """
    Seed the `access.Permission` registry before every DB-using test.

    Phase 3 made `RegistrationService.register` depend on seeded permissions
    (it creates system roles whose grants reference existing codes). We
    autouse this at the top level so tests in `accounts/`, `access/`, `core/`
    all get a populated permission table.
    """
    call_command("seed_rbac", verbosity=0)


# ---------------------------------------------------------------------------
# Phase 1 — tenancy
# ---------------------------------------------------------------------------
@pytest.fixture
def two_orgs(db) -> tuple[Organization, Organization]:
    alpha = Organization.objects.create(name="Alpha", slug="alpha")
    bravo = Organization.objects.create(name="Bravo", slug="bravo")
    return alpha, bravo


@pytest.fixture(scope="session")
def widget_model(django_db_setup, django_db_blocker):
    class Widget(TenantScopedModel):
        name = models.CharField(max_length=50)

        class Meta:
            app_label = "tenants"
            db_table = "test_widgets"

        def __str__(self) -> str:
            return self.name

    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.create_model(Widget)

    yield Widget

    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.delete_model(Widget)


# ---------------------------------------------------------------------------
# Phase 2 — identity
# ---------------------------------------------------------------------------
@pytest.fixture
def password() -> str:
    return PASSWORD


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user_factory(db):
    def _make(
        email: str = "user@example.com",
        password: str = PASSWORD,
        first_name: str = "First",
        last_name: str = "Last",
        **extra,
    ) -> User:
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **extra,
        )

    return _make


@pytest.fixture
def account_factory(db):
    def _make(
        *,
        user: User,
        organization: Organization,
        status: str = AccountStatus.ACTIVE,
        is_primary: bool = False,
    ) -> Account:
        return Account.objects.create(
            user=user,
            organization=organization,
            status=status,
            is_primary=is_primary,
            created_by=user,
            modified_by=user,
        )

    return _make


@pytest.fixture
def authed_client(api_client, user_factory, account_factory, two_orgs):
    """A logged-in APIClient for a user with one active account on Alpha."""
    alpha, _ = two_orgs
    user = user_factory(email="alice@example.com")
    account = account_factory(user=user, organization=alpha, is_primary=True)
    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200, response.content
    return api_client, user, account
