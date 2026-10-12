"""POST /api/auth/switch-organization/"""

from __future__ import annotations

import pytest
from django.conf import settings
from knox.models import AuthToken

from accounts.constants import AccountStatus

SWITCH_URL = "/api/auth/switch-organization/"


@pytest.mark.django_db
class TestSwitchOrganization:
    def test_requires_auth(self, api_client):
        response = api_client.post(SWITCH_URL, {"account_id": "00000000-0000-0000-0000-000000000000"})
        assert response.status_code == 401

    def test_happy_path_rotates_token_and_switches_context(self, authed_client, account_factory, two_orgs):
        client, user, alpha_account = authed_client
        _, bravo = two_orgs
        bravo_account = account_factory(user=user, organization=bravo)

        # Before switch: me is on alpha, exactly one token exists.
        before = client.get("/api/auth/me/").json()["data"]
        assert before["account"]["organization"]["slug"] == "alpha"
        assert AuthToken.objects.filter(user=user).count() == 1
        old_cookie = client.cookies[settings.AUTH_COOKIE_NAME].value

        # Switch.
        response = client.post(SWITCH_URL, {"account_id": str(bravo_account.public_id)}, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["account"]["organization"]["slug"] == "bravo"

        # New token exists; old token destroyed (count stays at 1 since switch
        # issues a new one after deleting the old).
        assert AuthToken.objects.filter(user=user).count() == 1
        new_cookie = client.cookies[settings.AUTH_COOKIE_NAME].value
        assert new_cookie != old_cookie

        # /me now reports bravo.
        after = client.get("/api/auth/me/").json()["data"]
        assert after["account"]["organization"]["slug"] == "bravo"

    def test_old_token_cannot_be_reused_after_switch(self, api_client, authed_client, account_factory, two_orgs):
        client, user, _ = authed_client
        _, bravo = two_orgs
        bravo_account = account_factory(user=user, organization=bravo)

        old_cookie = client.cookies[settings.AUTH_COOKIE_NAME].value
        client.post(SWITCH_URL, {"account_id": str(bravo_account.public_id)}, format="json")

        # A fresh client carrying only the OLD cookie must fail auth.
        from rest_framework.test import APIClient

        attacker = APIClient()
        attacker.cookies[settings.AUTH_COOKIE_NAME] = old_cookie
        response = attacker.get("/api/auth/me/")
        assert response.status_code == 401

    def test_account_id_not_owned_by_user(self, authed_client, account_factory, two_orgs, user_factory):
        client, _, _ = authed_client
        _, bravo = two_orgs
        other = user_factory(email="other@example.com")
        other_account = account_factory(user=other, organization=bravo)

        response = client.post(SWITCH_URL, {"account_id": str(other_account.public_id)}, format="json")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "switch_0001"

    def test_suspended_account_rejected(self, authed_client, account_factory, two_orgs):
        client, user, _ = authed_client
        _, bravo = two_orgs
        suspended = account_factory(user=user, organization=bravo, status=AccountStatus.SUSPENDED)

        response = client.post(SWITCH_URL, {"account_id": str(suspended.public_id)}, format="json")
        # Policy sees the account via owner-FK but rejects due to status.
        # Selector only looks at records (alive), so suspended is still
        # fetchable; policy's status check returns the switch_0002 code.
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "switch_0002"
