"""GET /api/auth/organizations/"""

from __future__ import annotations

import pytest

from accounts.constants import AccountStatus

ORGS_URL = "/api/auth/organizations/"


@pytest.mark.django_db
class TestMyOrganizations:
    def test_requires_auth(self, api_client):
        response = api_client.get(ORGS_URL)
        assert response.status_code == 401

    def test_returns_only_current_users_active_accounts(self, authed_client, account_factory, two_orgs, user_factory):
        client, user, _ = authed_client
        alpha, bravo = two_orgs

        # Give this user a second active account on bravo + one suspended account.
        active_bravo = account_factory(user=user, organization=bravo)
        account_factory(
            user=user_factory(email="other@example.com"), organization=bravo
        )  # another user — must not appear

        response = client.get(ORGS_URL)
        assert response.status_code == 200
        slugs = [a["organization"]["slug"] for a in response.json()["data"]]
        assert sorted(slugs) == ["alpha", "bravo"]
        assert str(active_bravo.public_id) in [a["id"] for a in response.json()["data"]]

    def test_excludes_non_active_statuses(self, authed_client, account_factory, two_orgs):
        client, user, _ = authed_client
        _, bravo = two_orgs
        account_factory(user=user, organization=bravo, status=AccountStatus.SUSPENDED)

        response = client.get(ORGS_URL)
        slugs = [a["organization"]["slug"] for a in response.json()["data"]]
        assert slugs == ["alpha"]
