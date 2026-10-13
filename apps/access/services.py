"""Write operations and business rules for roles and role assignments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from access.exceptions import (
    PermissionDenied as _PermissionDenied,
)
from access.exceptions import (
    RoleAssignmentError,
    RoleError,
    SeedError,
)
from access.models.assignment import RoleAssignment
from access.models.permission import Permission
from access.models.role import Role, RolePermission
from access.policies import RoleAssignmentPolicy
from access.registry import SYSTEM_ROLES
from core.exceptions import APIServiceError

if TYPE_CHECKING:
    from accounts.models.account import Account
    from accounts.models.user import User
    from tenants.models.organization import Organization


# Re-export so decorator imports stay stable at the services layer.
PermissionDenied = _PermissionDenied


class RoleService:
    @staticmethod
    @transaction.atomic
    def create_role(
        *,
        organization: Organization,
        name: str,
        description: str,
        permission_codes: list[str],
        created_by: User,
        code: str | None = None,
        is_system: bool = False,
    ) -> Role:
        if Role.records.for_organization(organization).filter(name=name).exists():
            raise APIServiceError(error_code=RoleError.NameTaken)

        permissions = list(Permission.records.filter(code__in=permission_codes))
        found_codes = {p.code for p in permissions}
        missing = set(permission_codes) - found_codes
        if missing:
            raise APIServiceError(error_code=RoleError.UnknownPermissionCode)

        role = Role.objects.create(
            organization=organization,
            name=name,
            description=description,
            code=code,
            is_system=is_system,
            created_by=created_by,
            modified_by=created_by,
        )
        RolePermission.objects.bulk_create([RolePermission(role=role, permission=p) for p in permissions])
        return role

    @staticmethod
    @transaction.atomic
    def update_role(
        *,
        role: Role,
        updated_by: User,
        name: str | None = None,
        description: str | None = None,
        permission_codes: list[str] | None = None,
    ) -> Role:
        if role.is_system:
            raise APIServiceError(error_code=RoleError.SystemRoleProtected)

        changed_fields: list[str] = []
        if name is not None and name != role.name:
            if Role.records.for_organization(role.organization).filter(name=name).exclude(pk=role.pk).exists():
                raise APIServiceError(error_code=RoleError.NameTaken)
            role.name = name
            changed_fields.append("name")
        if description is not None and description != role.description:
            role.description = description
            changed_fields.append("description")

        if changed_fields:
            role.modified_by = updated_by
            role.save(update_fields=[*changed_fields, "modified_by", "modified_at"])

        if permission_codes is not None:
            permissions = list(Permission.records.filter(code__in=permission_codes))
            if len(permissions) != len(set(permission_codes)):
                raise APIServiceError(error_code=RoleError.UnknownPermissionCode)
            # Hard-replace the set of grants. The through table has no audit
            # mixin, so a simple clear-and-insert is fine here.
            RolePermission.objects.filter(role=role).delete()
            RolePermission.objects.bulk_create([RolePermission(role=role, permission=p) for p in permissions])

        return role

    @staticmethod
    @transaction.atomic
    def delete_role(*, role: Role, deleted_by: User) -> None:
        if role.is_system:
            raise APIServiceError(error_code=RoleError.SystemRoleProtected)
        role.delete(deleted_by=deleted_by)

    @staticmethod
    @transaction.atomic
    def create_system_roles_for_organization(
        *,
        organization: Organization,
        created_by: User,
    ) -> dict[str, Role]:
        """
        Idempotently seed the four system roles for a new organization.
        Safe to call twice; keyed on (organization, code).
        """
        permissions_by_code = {p.code: p for p in Permission.records.all()}
        if not permissions_by_code:
            raise APIServiceError(error_code=SeedError.PermissionsMissing)

        results: dict[str, Role] = {}
        for role_def in SYSTEM_ROLES:
            # verify every referenced code exists in the DB
            missing = [c for c in role_def.permission_codes if c not in permissions_by_code]
            if missing:
                raise APIServiceError(error_code=SeedError.PermissionsMissing)

            role, created = Role.records.for_organization(organization).get_or_create(
                code=role_def.code,
                is_system=True,
                defaults={
                    "organization": organization,
                    "name": role_def.name,
                    "description": role_def.description,
                    "created_by": created_by,
                    "modified_by": created_by,
                },
            )
            # Reset grants to match the registry on every call — keeps system
            # roles in lockstep with `registry.py`.
            RolePermission.objects.filter(role=role).delete()
            RolePermission.objects.bulk_create(
                [RolePermission(role=role, permission=permissions_by_code[c]) for c in role_def.permission_codes]
            )
            results[role_def.code] = role
        return results


class RoleAssignmentService:
    @staticmethod
    @transaction.atomic
    def assign(
        *,
        account: Account,
        role: Role,
        assigned_by: User,
    ) -> RoleAssignment:
        if account.organization_id != role.organization_id:
            raise APIServiceError(error_code=RoleAssignmentError.CrossOrganization)

        assignment, created = RoleAssignment.records.get_or_create(
            account=account,
            role=role,
            defaults={
                "created_by": assigned_by,
                "modified_by": assigned_by,
                "is_active": True,
            },
        )
        if not created and not assignment.is_active:
            assignment.is_active = True
            assignment.modified_by = assigned_by
            assignment.save(update_fields=["is_active", "modified_by", "modified_at"])
        return assignment

    @staticmethod
    @transaction.atomic
    def revoke(*, assignment: RoleAssignment, revoked_by: User) -> None:
        if RoleAssignmentPolicy.would_strand_organization_without_owner(assignment):
            raise APIServiceError(error_code=RoleAssignmentError.LastOwner)
        assignment.delete(deleted_by=revoked_by)
