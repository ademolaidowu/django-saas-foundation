"""
HEADLINE Phase 3 test: an organization must always have at least one active
Owner. Revoking the last Owner assignment is a 400 with a specific error code.
"""

from __future__ import annotations

import pytest

from access.models.assignment import RoleAssignment

ASSIGN_URL = "/api/access/role-assignments/"


@pytest.fixture
def two_owner_setup(authed_client, grant, two_orgs, user_factory, account_factory, system_roles_for):
    """
    Alpha has TWO accounts, both assigned Owner. The authed client is the first.
    """
    client, user, owner_account = authed_client
    alpha, _ = two_orgs
    system_roles_for(alpha, user)
    grant(account=owner_account, organization=alpha, role_code="owner", assigned_by=user)

    second_user = user_factory(email="second@example.com")
    second_account = account_factory(user=second_user, organization=alpha)
    grant(account=second_account, organization=alpha, role_code="owner", assigned_by=user)
    return client, owner_account, second_account, alpha


@pytest.mark.django_db
class TestLastOwnerProtection:
    def test_revoking_one_of_two_owners_is_ok(self, two_owner_setup):
        client, _, second_account, _ = two_owner_setup

        second_owner = RoleAssignment.records.get(account=second_account, role__code="owner")
        response = client.delete(f"{ASSIGN_URL}{second_owner.public_id}/")
        assert response.status_code == 204

    def test_revoking_the_last_owner_is_rejected(self, two_owner_setup):
        client, owner_account, second_account, _ = two_owner_setup

        # Revoke one — leaves exactly one Owner.
        second_owner = RoleAssignment.records.get(account=second_account, role__code="owner")
        assert client.delete(f"{ASSIGN_URL}{second_owner.public_id}/").status_code == 204

        # Attempt to revoke the LAST one.
        last_owner = RoleAssignment.records.get(account=owner_account, role__code="owner")
        response = client.delete(f"{ASSIGN_URL}{last_owner.public_id}/")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "role_assignment_0004"

    def test_db_state_unchanged_after_rejected_revoke(self, two_owner_setup):
        """If the last-Owner check fires, nothing was mutated."""
        client, owner_account, second_account, _ = two_owner_setup
        second_owner = RoleAssignment.records.get(account=second_account, role__code="owner")
        client.delete(f"{ASSIGN_URL}{second_owner.public_id}/")

        last_owner = RoleAssignment.records.get(account=owner_account, role__code="owner")
        before = (last_owner.is_active, last_owner.deleted_at)
        client.delete(f"{ASSIGN_URL}{last_owner.public_id}/")
        last_owner.refresh_from_db()
        after = (last_owner.is_active, last_owner.deleted_at)
        assert before == after
