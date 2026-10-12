"""GET /api/auth/me/"""

from __future__ import annotations

import pytest

ME_URL = "/api/auth/me/"


@pytest.mark.django_db
class TestMe:
    def test_requires_auth(self, api_client):
        response = api_client.get(ME_URL)
        assert response.status_code == 401

    def test_returns_user_and_account_derived_from_token(self, authed_client, two_orgs):
        client, user, account = authed_client
        alpha, _ = two_orgs

        response = client.get(ME_URL)
        assert response.status_code == 200

        body = response.json()["data"]
        assert body["user"]["email"] == user.email
        assert body["account"]["id"] == str(account.public_id)
        assert body["account"]["organization"]["slug"] == alpha.slug
