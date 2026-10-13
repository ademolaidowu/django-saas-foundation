"""Role assignment create + revoke."""

from __future__ import annotations

import pytest

from access.models.assignment import RoleAssignment

ASSIGN_URL = "/api/access/role-assignments/"


@pytest.fixture
def owner_setup(authed_client, grant, two_orgs, user_factory, account_factory, system_roles_for):
    """
    Owner-authed client on Alpha, plus a second user + account on Alpha
    that we can assign roles to.
    """
    client, user, owner_account = authed_client
    alpha, bravo = two_orgs
    system_roles_for(alpha, user)
    system_roles_for(bravo, user)
    grant(account=owner_account, organization=alpha, role_code="owner", assigned_by=user)

    other_user = user_factory(email="other@example.com")
    other_account = account_factory(user=other_user, organization=alpha)
    return client, user, owner_account, other_account, alpha, bravo


@pytest.mark.django_db
class TestRoleAssignmentCreate:
    def test_happy_path(self, owner_setup):
        client, _, _, other_account, alpha, _ = owner_setup

        roles_resp = client.get("/api/access/roles/")
        member_role_id = next(r["id"] for r in roles_resp.json()["data"] if r["code"] == "member")

        response = client.post(
            ASSIGN_URL,
            {"account_id": str(other_account.public_id), "role_id": member_role_id},
            format="json",
        )
        assert response.status_code == 201, response.content
        assert RoleAssignment.records.filter(account=other_account, role__code="member", is_active=True).exists()

    def test_cross_organization_rejected(self, owner_setup):
        """Can't assign a Bravo role to an Alpha account."""
        from access.models.role import Role

        client, _, _, other_account, alpha, bravo = owner_setup
        bravo_member = Role.records.for_organization(bravo).get(code="member")

        response = client.post(
            ASSIGN_URL,
            {"account_id": str(other_account.public_id), "role_id": str(bravo_member.public_id)},
            format="json",
        )
        # 404 — a Bravo role is not visible to an Alpha-scoped client.
        assert response.status_code == 404

    def test_duplicate_assignment_is_noop(self, owner_setup):
        client, _, _, other_account, _, _ = owner_setup
        roles_resp = client.get("/api/access/roles/")
        viewer_id = next(r["id"] for r in roles_resp.json()["data"] if r["code"] == "viewer")

        for _ in range(2):
            r = client.post(
                ASSIGN_URL,
                {"account_id": str(other_account.public_id), "role_id": viewer_id},
                format="json",
            )
            assert r.status_code == 201

        assert RoleAssignment.records.filter(account=other_account, role__code="viewer").count() == 1


@pytest.mark.django_db
class TestRoleAssignmentRevoke:
    def test_revoke_deactivates(self, owner_setup):
        client, _, _, other_account, _, _ = owner_setup
        roles_resp = client.get("/api/access/roles/")
        viewer_id = next(r["id"] for r in roles_resp.json()["data"] if r["code"] == "viewer")

        created = client.post(
            ASSIGN_URL,
            {"account_id": str(other_account.public_id), "role_id": viewer_id},
            format="json",
        ).json()["data"]

        response = client.delete(f"{ASSIGN_URL}{created['id']}/")
        assert response.status_code == 204
        # Soft-deleted; not visible in `records`.
        assert not RoleAssignment.records.filter(public_id=created["id"]).exists()

    def test_revoke_unknown_returns_404(self, owner_setup):
        client, _, _, _, _, _ = owner_setup
        import uuid as _uuid

        response = client.delete(f"{ASSIGN_URL}{_uuid.uuid4()}/")
        assert response.status_code == 404
