"""Read-only lookups for the access app."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db.models import QuerySet

from access.models.assignment import RoleAssignment
from access.models.permission import Permission
from access.models.role import Role

if TYPE_CHECKING:
    from accounts.models.account import Account
    from tenants.models.organization import Organization


class PermissionSelectors:
    @staticmethod
    def all() -> QuerySet[Permission]:
        return Permission.records.all().order_by("module", "code")

    @staticmethod
    def account_has_permission(account: Account, code: str) -> bool:
        """
        True iff the account has at least one active, non-deleted role
        assignment to a role that grants the given permission code.
        """
        return RoleAssignment.records.filter(
            account=account,
            is_active=True,
            role__deleted_at__isnull=True,
            role__role_permissions__deleted_at__isnull=True,
            role__role_permissions__permission__code=code,
        ).exists()


class RoleSelectors:
    @staticmethod
    def list_for_organization(organization: Organization) -> QuerySet[Role]:
        return (
            Role.records.for_organization(organization).prefetch_related("permissions").order_by("-is_system", "name")
        )

    @staticmethod
    def get_by_public_id(organization: Organization, public_id: uuid.UUID) -> Role | None:
        return (
            Role.records.for_organization(organization)
            .filter(public_id=public_id)
            .prefetch_related("permissions")
            .first()
        )

    @staticmethod
    def get_system_role(organization: Organization, code: str) -> Role | None:
        return Role.records.for_organization(organization).filter(code=code, is_system=True).first()


class RoleAssignmentSelectors:
    @staticmethod
    def get_by_public_id(public_id: uuid.UUID) -> RoleAssignment | None:
        return (
            RoleAssignment.records.filter(public_id=public_id)
            .select_related("account", "role", "role__organization")
            .first()
        )

    @staticmethod
    def count_active_owners(organization: Organization) -> int:
        from access.constants import SystemRoleCode

        return RoleAssignment.records.filter(
            role__organization=organization,
            role__code=SystemRoleCode.OWNER,
            role__is_system=True,
            is_active=True,
        ).count()
