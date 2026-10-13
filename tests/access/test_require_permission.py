"""The @require_permission decorator — allow / deny with 403."""

from __future__ import annotations

import pytest
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from access.decorators import require_permission


class ProbeView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("permissions.read")
    def get(self, request, *args, **kwargs):
        return Response({"ok": True})


_URLPATTERNS = __import__("django.urls", fromlist=["path", "include"])
urlpatterns = [
    _URLPATTERNS.path("api/auth/", _URLPATTERNS.include("accounts.urls", namespace="accounts")),
    _URLPATTERNS.path("probe/perm/", ProbeView.as_view()),
]


@pytest.mark.django_db
@pytest.mark.urls(__name__)
class TestRequirePermission:
    def test_allows_when_permission_present(self, authed_client, system_roles_for, grant, two_orgs):
        client, user, account = authed_client
        alpha, _ = two_orgs
        system_roles_for(alpha, user)
        grant(account=account, organization=alpha, role_code="owner", assigned_by=user)

        response = client.get("/probe/perm/")
        assert response.status_code == 200

    def test_denies_with_403_when_missing(self, authed_client, system_roles_for, grant, two_orgs):
        """
        Member role lacks `permissions.read` (Member has domain CRUD codes
        plus `accounts.read` — see registry.MEMBER_CODES).
        """
        client, user, account = authed_client
        alpha, _ = two_orgs
        system_roles_for(alpha, user)
        grant(account=account, organization=alpha, role_code="member", assigned_by=user)

        response = client.get("/probe/perm/")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "access_0001"

    def test_denies_with_403_when_account_has_no_roles(self, authed_client):
        """Fresh account with zero role assignments — must still 403, not crash."""
        client, _, _ = authed_client

        response = client.get("/probe/perm/")
        assert response.status_code == 403
