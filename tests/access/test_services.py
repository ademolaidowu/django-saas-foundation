"""Direct unit tests for access services."""

from __future__ import annotations

import pytest

from access.exceptions import RoleAssignmentError, RoleError, SeedError
from access.models.permission import Permission
from access.models.role import Role, RolePermission
from access.policies import RoleAssignmentPolicy
from access.services import RoleAssignmentService, RoleService
from core.exceptions import APIServiceError


@pytest.mark.django_db
class TestRoleService:
    def test_create_role_rejects_unknown_permission_code(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        with pytest.raises(APIServiceError) as exc:
            RoleService.create_role(
                organization=alpha,
                name="Nope",
                description="",
                permission_codes=["does.not.exist"],
                created_by=user,
            )
        assert exc.value.error_code is RoleError.UnknownPermissionCode

    def test_create_role_rejects_duplicate_name(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        RoleService.create_role(
            organization=alpha,
            name="Dup",
            description="",
            permission_codes=[],
            created_by=user,
        )
        with pytest.raises(APIServiceError) as exc:
            RoleService.create_role(
                organization=alpha,
                name="Dup",
                description="",
                permission_codes=[],
                created_by=user,
            )
        assert exc.value.error_code is RoleError.NameTaken

    def test_update_role_rejects_system_role(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        with pytest.raises(APIServiceError) as exc:
            RoleService.update_role(role=roles["owner"], updated_by=user, name="Renamed")
        assert exc.value.error_code is RoleError.SystemRoleProtected

    def test_update_role_name_conflict(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        RoleService.create_role(organization=alpha, name="A", description="", permission_codes=[], created_by=user)
        role_b = RoleService.create_role(
            organization=alpha, name="B", description="", permission_codes=[], created_by=user
        )
        with pytest.raises(APIServiceError) as exc:
            RoleService.update_role(role=role_b, updated_by=user, name="A")
        assert exc.value.error_code is RoleError.NameTaken

    def test_update_role_no_changes_is_noop(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        role = RoleService.create_role(
            organization=alpha, name="X", description="d", permission_codes=[], created_by=user
        )
        modified_before = role.modified_at
        RoleService.update_role(role=role, updated_by=user, name="X", description="d")
        role.refresh_from_db()
        # No change recorded
        assert role.modified_at == modified_before

    def test_delete_role_rejects_system_role(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        with pytest.raises(APIServiceError) as exc:
            RoleService.delete_role(role=roles["admin"], deleted_by=user)
        assert exc.value.error_code is RoleError.SystemRoleProtected

    def test_create_system_roles_requires_seeded_permissions(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        # Blow away all permissions so the seed guard trips.
        RolePermission.objects.all().delete()
        Permission.objects.all().delete()
        with pytest.raises(APIServiceError) as exc:
            RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        assert exc.value.error_code is SeedError.PermissionsMissing

    def test_create_system_roles_is_idempotent(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        assert Role.records.for_organization(alpha).filter(is_system=True).count() == 4


@pytest.mark.django_db
class TestRoleAssignmentService:
    def test_assign_rejects_cross_organization(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        alpha_account = account_factory(user=user, organization=alpha)
        bravo_user = user_factory(email="y@example.com")
        bravo_roles = RoleService.create_system_roles_for_organization(organization=bravo, created_by=bravo_user)
        with pytest.raises(APIServiceError) as exc:
            RoleAssignmentService.assign(
                account=alpha_account,
                role=bravo_roles["viewer"],
                assigned_by=user,
            )
        assert exc.value.error_code is RoleAssignmentError.CrossOrganization

    def test_assign_reactivates_inactive_assignment(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        a = RoleAssignmentService.assign(account=account, role=roles["viewer"], assigned_by=user)
        a.is_active = False
        a.save(update_fields=["is_active"])

        a2 = RoleAssignmentService.assign(account=account, role=roles["viewer"], assigned_by=user)
        assert a2.pk == a.pk
        assert a2.is_active is True


@pytest.mark.django_db
class TestRoleAssignmentPolicy:
    def test_would_strand_true_when_only_one_owner_left(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        assignment = RoleAssignmentService.assign(account=account, role=roles["owner"], assigned_by=user)
        assert RoleAssignmentPolicy.would_strand_organization_without_owner(assignment) is True

    def test_would_strand_false_for_non_owner_role(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        viewer_assignment = RoleAssignmentService.assign(account=account, role=roles["viewer"], assigned_by=user)
        assert RoleAssignmentPolicy.would_strand_organization_without_owner(viewer_assignment) is False
