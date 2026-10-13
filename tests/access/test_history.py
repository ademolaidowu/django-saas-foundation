"""
Role / RoleAssignment history captures the acting user via
`simple_history.middleware.HistoryRequestMiddleware`.
"""

from __future__ import annotations

import pytest

from access.constants import SystemRoleCode
from access.models.assignment import RoleAssignment
from access.models.role import Role
from access.services import RoleAssignmentService, RoleService

ROLES_URL = "/api/access/roles/"
ASSIGN_URL = "/api/access/role-assignments/"


@pytest.fixture
def owner_client(authed_client, two_orgs):
    """Alice is Owner on Alpha, logged in."""
    client, user, account = authed_client
    alpha, _ = two_orgs
    roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
    RoleAssignmentService.assign(account=account, role=roles[SystemRoleCode.OWNER], assigned_by=user)
    return client, user, account, alpha


@pytest.mark.django_db
class TestRoleHistory:
    def test_create_role_writes_plus_history_with_user(self, owner_client):
        client, user, _, alpha = owner_client

        response = client.post(
            ROLES_URL,
            {"name": "Custom", "permission_codes": ["projects.read"]},
            format="json",
        )
        assert response.status_code == 201
        role = Role.records.for_organization(alpha).get(name="Custom")

        history = list(role.history.all())
        assert len(history) == 1
        assert history[0].history_type == "+"
        assert history[0].history_user_id == user.id

    def test_update_role_writes_tilde_history(self, owner_client):
        client, user, _, _ = owner_client
        created = client.post(
            ROLES_URL,
            {"name": "To rename", "permission_codes": []},
            format="json",
        ).json()["data"]

        patched = client.patch(
            f"{ROLES_URL}{created['id']}/",
            {"name": "Renamed"},
            format="json",
        )
        assert patched.status_code == 200

        role = Role.objects.unsafe_all().get(public_id=created["id"])
        history = list(role.history.all().order_by("-history_date"))
        # [update, create]
        assert history[0].history_type == "~"
        assert history[0].history_user_id == user.id


@pytest.mark.django_db
class TestRoleAssignmentHistory:
    def test_assign_writes_plus_history_with_user(self, owner_client, user_factory, account_factory):
        client, user, _, alpha = owner_client
        bob = user_factory(email="bob@example.com")
        bob_account = account_factory(user=bob, organization=alpha, is_primary=False)

        viewer_role = Role.records.for_organization(alpha).get(code=SystemRoleCode.VIEWER)
        response = client.post(
            ASSIGN_URL,
            {
                "account_id": str(bob_account.public_id),
                "role_id": str(viewer_role.public_id),
            },
            format="json",
        )
        assert response.status_code == 201
        assignment = RoleAssignment.records.get(account=bob_account, role=viewer_role)
        history = list(assignment.history.all())
        assert len(history) == 1
        assert history[0].history_type == "+"
        assert history[0].history_user_id == user.id

    def test_revoke_writes_tilde_history_with_deleted_at(self, owner_client, user_factory, account_factory):
        """
        Revoking a role assignment is a *soft* delete — the row stays and
        `deleted_at` is stamped. Simple-history records this as `~` (change),
        not `-` (hard delete), with the acting user attributed via the
        middleware.
        """
        client, user, _, alpha = owner_client
        bob = user_factory(email="bob@example.com")
        bob_account = account_factory(user=bob, organization=alpha, is_primary=False)
        viewer_role = Role.records.for_organization(alpha).get(code=SystemRoleCode.VIEWER)

        created = client.post(
            ASSIGN_URL,
            {
                "account_id": str(bob_account.public_id),
                "role_id": str(viewer_role.public_id),
            },
            format="json",
        ).json()["data"]
        client.delete(f"{ASSIGN_URL}{created['id']}/")

        # RoleAssignment is NOT TenantScopedModel; `.objects` already returns
        # soft-deleted rows via BaseManager.
        assignment = RoleAssignment.objects.get(public_id=created["id"])
        history = list(assignment.history.all().order_by("-history_date"))
        latest = history[0]
        assert latest.history_type == "~"
        assert latest.history_user_id == user.id
        assert latest.deleted_at is not None
