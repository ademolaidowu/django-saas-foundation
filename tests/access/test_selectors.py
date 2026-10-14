"""Direct unit tests for access selectors."""

from __future__ import annotations

import uuid

import pytest

from access.selectors import (
    PermissionSelectors,
    RoleAssignmentSelectors,
    RoleSelectors,
)
from access.services import RoleAssignmentService, RoleService


@pytest.mark.django_db
class TestPermissionSelectors:
    def test_all_returns_seeded_rows(self):
        results = list(PermissionSelectors.all())
        codes = {p.code for p in results}
        assert "projects:read" in codes
        assert "roles:create" in codes

    def test_account_has_permission_true(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        RoleAssignmentService.assign(account=account, role=roles["owner"], assigned_by=user)
        assert PermissionSelectors.account_has_permission(account, "projects:read")

    def test_account_has_permission_false_when_no_role(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        assert not PermissionSelectors.account_has_permission(account, "projects:read")

    def test_account_has_permission_false_when_inactive(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        a = RoleAssignmentService.assign(account=account, role=roles["owner"], assigned_by=user)
        a.is_active = False
        a.save(update_fields=["is_active"])
        assert not PermissionSelectors.account_has_permission(account, "projects:read")


@pytest.mark.django_db
class TestRoleSelectors:
    def test_list_for_organization_scoped(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        alpha_user = user_factory(email="a@example.com")
        bravo_user = user_factory(email="b@example.com")
        RoleService.create_system_roles_for_organization(organization=alpha, created_by=alpha_user)
        RoleService.create_system_roles_for_organization(organization=bravo, created_by=bravo_user)
        alpha_roles = {r.code for r in RoleSelectors.list_for_organization(alpha)}
        assert alpha_roles == {"owner", "admin", "member", "viewer"}

    def test_get_by_public_id_miss(self, two_orgs):
        alpha, _ = two_orgs
        assert RoleSelectors.get_by_public_id(alpha, uuid.uuid4()) is None

    def test_get_system_role(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        owner_role = RoleSelectors.get_system_role(alpha, "owner")
        assert owner_role is not None and owner_role.code == "owner"


@pytest.mark.django_db
class TestRoleAssignmentSelectors:
    def test_count_active_owners(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        RoleAssignmentService.assign(account=account, role=roles["owner"], assigned_by=user)
        assert RoleAssignmentSelectors.count_active_owners(alpha) == 1

    def test_get_by_public_id_miss(self):
        assert RoleAssignmentSelectors.get_by_public_id(uuid.uuid4()) is None
