"""POST /api/auth/login/"""

from __future__ import annotations

import pytest
from django.conf import settings

from accounts.constants import AccountStatus

LOGIN_URL = "/api/auth/login/"


@pytest.mark.django_db
class TestLogin:
    def test_happy_path(self, api_client, user_factory, account_factory, two_orgs, password):
        alpha, _ = two_orgs
        user = user_factory(email="a@example.com")
        account_factory(user=user, organization=alpha, is_primary=True)

        response = api_client.post(LOGIN_URL, {"email": "a@example.com", "password": password}, format="json")

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["user"]["email"] == "a@example.com"
        assert body["account"]["organization"]["slug"] == "alpha"
        assert settings.AUTH_COOKIE_NAME in response.cookies

    def test_wrong_password(self, api_client, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="a@example.com")
        account_factory(user=user, organization=alpha, is_primary=True)

        response = api_client.post(LOGIN_URL, {"email": "a@example.com", "password": "wrong"}, format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "login_0001"

    def test_unknown_email(self, api_client, password):
        response = api_client.post(LOGIN_URL, {"email": "ghost@example.com", "password": password}, format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "login_0001"

    def test_no_active_account(self, api_client, user_factory, account_factory, two_orgs, password):
        alpha, _ = two_orgs
        user = user_factory(email="suspended@example.com")
        account_factory(user=user, organization=alpha, status=AccountStatus.SUSPENDED)

        response = api_client.post(
            LOGIN_URL,
            {"email": "suspended@example.com", "password": password},
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "login_0003"

    def test_primary_wins_over_other_active_accounts(
        self, api_client, user_factory, account_factory, two_orgs, password
    ):
        """User with accounts in both orgs — login binds to the primary one."""
        alpha, bravo = two_orgs
        user = user_factory(email="multi@example.com")
        account_factory(user=user, organization=alpha, is_primary=False)
        account_factory(user=user, organization=bravo, is_primary=True)

        response = api_client.post(LOGIN_URL, {"email": "multi@example.com", "password": password}, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["account"]["organization"]["slug"] == "bravo"
