"""POST /api/auth/register/"""

from __future__ import annotations

import pytest
from django.conf import settings

from accounts.constants import AccountStatus
from accounts.models.account import Account
from accounts.models.token import AccountToken
from accounts.models.user import User
from tenants.models.organization import Organization

REGISTER_URL = "/api/auth/register/"


def _payload(**overrides):
    base = {
        "email": "owner@example.com",
        "password": "testpassword123",
        "first_name": "Owner",
        "last_name": "Example",
        "organization_name": "Owner Co",
        "organization_slug": "owner-co",
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
class TestRegister:
    def test_happy_path(self, api_client):
        response = api_client.post(REGISTER_URL, _payload(), format="json")
        assert response.status_code == 201

        body = response.json()["data"]
        assert body["user"]["email"] == "owner@example.com"
        assert body["account"]["organization"]["slug"] == "owner-co"
        assert body["account"]["is_primary"] is True
        assert body["account"]["status"] == AccountStatus.ACTIVE

        # DB side-effects
        user = User.objects.get(email="owner@example.com")
        org = Organization.objects.get(slug="owner-co")
        account = Account.objects.get(user=user, organization=org)
        assert account.is_primary and account.status == AccountStatus.ACTIVE
        assert AccountToken.objects.filter(account=account).count() == 1

        # Cookie set
        assert settings.AUTH_COOKIE_NAME in response.cookies

    def test_duplicate_email_rejected(self, api_client, user_factory):
        user_factory(email="dup@example.com")
        response = api_client.post(REGISTER_URL, _payload(email="dup@example.com"), format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "registration_0001"

    def test_duplicate_slug_rejected(self, api_client, user_factory, account_factory, two_orgs):
        response = api_client.post(REGISTER_URL, _payload(organization_slug="alpha"), format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "registration_0002"

    def test_short_password_rejected(self, api_client):
        response = api_client.post(REGISTER_URL, _payload(password="short"), format="json")
        assert response.status_code == 400

    def test_atomicity_rolls_back_user_on_org_failure(self, api_client, two_orgs):
        # Slug collision happens AFTER user would otherwise be created; the
        # transaction must roll back so no orphan user remains.
        response = api_client.post(REGISTER_URL, _payload(organization_slug="alpha"), format="json")
        assert response.status_code == 400
        assert not User.objects.filter(email="owner@example.com").exists()
