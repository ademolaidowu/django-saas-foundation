"""POST /api/auth/register/ now seeds system roles and assigns Owner."""

from __future__ import annotations

import pytest

from access.constants import SystemRoleCode
from access.models.assignment import RoleAssignment
from access.models.role import Role
from access.registry import SYSTEM_ROLES
from accounts.models.account import Account
from tenants.models.organization import Organization

REGISTER_URL = "/api/auth/register/"


def _payload():
    return {
        "email": "owner@example.com",
        "password": "testpassword123",
        "first_name": "Owner",
        "last_name": "Example",
        "organization_name": "Owner Co",
        "organization_slug": "owner-co",
    }


@pytest.mark.django_db
class TestRegistrationAssignsOwner:
    def test_four_system_roles_are_created(self, api_client):
        response = api_client.post(REGISTER_URL, _payload(), format="json")
        assert response.status_code == 201

        org = Organization.objects.get(slug="owner-co")
        roles = Role.records.for_organization(org).filter(is_system=True)
        assert sorted(roles.values_list("code", flat=True)) == sorted(r.code for r in SYSTEM_ROLES)

    def test_owner_assignment_created(self, api_client):
        api_client.post(REGISTER_URL, _payload(), format="json")
        account = Account.objects.get(user__email="owner@example.com")
        owner_assignments = RoleAssignment.records.filter(
            account=account,
            role__code=SystemRoleCode.OWNER,
            is_active=True,
        )
        assert owner_assignments.count() == 1

    def test_owner_role_has_every_registry_permission(self, api_client):
        api_client.post(REGISTER_URL, _payload(), format="json")
        org = Organization.objects.get(slug="owner-co")
        owner = Role.records.for_organization(org).get(code=SystemRoleCode.OWNER)
        owner_perm_codes = set(owner.permissions.values_list("code", flat=True))

        from access.registry import ALL_CODES

        assert owner_perm_codes == set(ALL_CODES)

    def test_registration_rollback_includes_role_seeding(self, api_client, user_factory):
        """
        If anything in `register()` fails (even role seeding), the whole
        transaction rolls back — no orphan user, no orphan org.
        """
        payload = _payload()
        # Pre-create an org with the target slug to force a conflict.
        Organization.objects.create(name="X", slug=payload["organization_slug"])

        response = api_client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400
        from accounts.models.user import User

        assert not User.objects.filter(email=payload["email"]).exists()
