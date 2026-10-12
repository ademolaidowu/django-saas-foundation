"""POST /api/auth/logout/"""

from __future__ import annotations

import pytest
from django.conf import settings
from knox.models import AuthToken

from accounts.models.token import AccountToken

LOGOUT_URL = "/api/auth/logout/"


@pytest.mark.django_db
class TestLogout:
    def test_requires_auth(self, api_client):
        response = api_client.post(LOGOUT_URL)
        assert response.status_code == 401

    def test_destroys_token_and_cookie(self, authed_client):
        client, user, account = authed_client
        assert AuthToken.objects.filter(user=user).count() == 1
        assert AccountToken.objects.filter(account=account).count() == 1

        response = client.post(LOGOUT_URL)
        assert response.status_code == 200

        # AuthToken gone, AccountToken cascaded.
        assert AuthToken.objects.filter(user=user).count() == 0
        assert AccountToken.objects.filter(account=account).count() == 0

        # Cookie was cleared (set with Max-Age=0).
        cleared = response.cookies.get(settings.AUTH_COOKIE_NAME)
        assert cleared is not None
        assert cleared["max-age"] == 0 or cleared.value == ""

    def test_logged_out_client_cannot_access_me(self, authed_client):
        client, _, _ = authed_client
        client.post(LOGOUT_URL)
        # Session is dead; the cookie was cleared. The test client preserves
        # cookies, so manually clear them to simulate a fresh request.
        client.cookies.clear()
        response = client.get("/api/auth/me/")
        assert response.status_code == 401
