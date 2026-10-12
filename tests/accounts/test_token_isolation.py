"""
Headline test for Phase 2.

A user holds two active accounts across two organizations. The token issued
for Account A on Org Alpha must only be able to see Alpha's data; it cannot
be re-aimed at Bravo. Switching to Account B issues a new token (and
invalidates the old one) that sees only Bravo's data.

The probe endpoints (see `_isolation_urls.py`) are the test harness — they
expose `request.organization.slug` and a widget count scoped by it, which is
how we prove that the authentication class derived the org context from the
token chain and nothing else.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from accounts.models.token import AccountToken

from . import _isolation_urls
from .conftest import PASSWORD


@pytest.fixture
def probe_setup(widget_model, two_orgs, user_factory, account_factory):
    """
    Create: 1 user with 2 active accounts (primary=Alpha), 1 widget per org.
    Hand the widget model to the probe URLconf so its view can query it.
    """
    _isolation_urls.set_widget_model(widget_model)

    alpha, bravo = two_orgs
    user = user_factory(email="multi@example.com")
    alpha_account = account_factory(user=user, organization=alpha, is_primary=True)
    bravo_account = account_factory(user=user, organization=bravo)

    widget_model.objects.create(organization=alpha, name="alpha-widget")
    widget_model.objects.create(organization=bravo, name="bravo-widget")

    return user, alpha_account, bravo_account, alpha, bravo


def _login(client: APIClient, email: str) -> None:
    response = client.post("/api/auth/login/", {"email": email, "password": PASSWORD}, format="json")
    assert response.status_code == 200, response.content


@pytest.mark.django_db
@pytest.mark.urls("tests.accounts._isolation_urls")
class TestTokenIsolation:
    def test_token_binds_organization_from_primary_account(self, probe_setup):
        """Login → request.organization == Alpha, visible widget count = 1."""
        user, alpha_account, _, _, _ = probe_setup
        client = APIClient()
        _login(client, user.email)

        probe = client.get("/probe/me/").json()["data"]
        assert probe["organization_slug"] == "alpha"

        widgets = client.get("/probe/widgets/").json()["data"]
        assert widgets["count"] == 1  # only alpha-widget — bravo-widget filtered out

    def test_switch_rebinds_organization_and_rotates_token(self, probe_setup):
        """After switch to Bravo account, token sees Bravo-only."""
        user, _, bravo_account, _, _ = probe_setup
        client = APIClient()
        _login(client, user.email)

        response = client.post(
            "/api/auth/switch-organization/",
            {"account_id": str(bravo_account.public_id)},
            format="json",
        )
        assert response.status_code == 200

        probe = client.get("/probe/me/").json()["data"]
        assert probe["organization_slug"] == "bravo"

        widgets = client.get("/probe/widgets/").json()["data"]
        assert widgets["count"] == 1  # only bravo-widget

    def test_old_token_rejected_after_switch(self, probe_setup):
        """Capture the Alpha cookie, switch, then prove the old cookie no longer works."""
        user, _, bravo_account, _, _ = probe_setup
        client = APIClient()
        _login(client, user.email)
        old_cookie = client.cookies[settings.AUTH_COOKIE_NAME].value

        client.post(
            "/api/auth/switch-organization/",
            {"account_id": str(bravo_account.public_id)},
            format="json",
        )

        stale = APIClient()
        stale.cookies[settings.AUTH_COOKIE_NAME] = old_cookie
        response = stale.get("/probe/me/")
        assert response.status_code == 401

    def test_token_with_deleted_account_context_rejected(self, probe_setup):
        """
        If an attacker tampers with the chain — e.g. the AccountToken row is
        deleted but the Knox AuthToken remains — authentication must fail.
        Proves that the auth class requires the full chain on every request.
        """
        user, _, _, _, _ = probe_setup
        client = APIClient()
        _login(client, user.email)

        AccountToken.objects.all().delete()

        response = client.get("/probe/me/")
        assert response.status_code == 401

    def test_cross_org_data_leak_impossible(self, probe_setup):
        """
        Belt-and-braces: even with a valid token, direct manipulation of a
        TenantScopedQuerySet without `.for_organization(...)` must raise. This
        is Phase 1's guarantee re-expressed in the Phase 2 integration path.
        """
        from core.exceptions import UnscopedQueryError

        user, _, _, _, _ = probe_setup
        client = APIClient()
        _login(client, user.email)

        widget_model = _isolation_urls._WIDGET_MODEL
        with pytest.raises(UnscopedQueryError):
            list(widget_model.records.all())
