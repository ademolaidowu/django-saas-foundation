"""Fixtures shared by all accounts tests."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from accounts.constants import AccountStatus
from accounts.models.account import Account
from accounts.models.user import User
from tenants.models.organization import Organization

PASSWORD = "testpassword123"


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
