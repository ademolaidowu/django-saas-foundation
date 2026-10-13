"""Fixtures for the access tests."""

from __future__ import annotations

import pytest

from access.constants import SystemRoleCode
from access.models.role import Role
from access.services import RoleAssignmentService, RoleService


@pytest.fixture
def system_roles_for(db):
    """Factory: seed the four system roles for an organization, return as a dict."""

    def _make(organization, created_by) -> dict[str, Role]:
        return RoleService.create_system_roles_for_organization(
            organization=organization,
            created_by=created_by,
        )

    return _make


@pytest.fixture
def grant(db):
    """Factory: assign a system role (by code) to an account."""

    def _grant(*, account, organization, role_code: str, assigned_by):
        role = Role.records.for_organization(organization).filter(code=role_code, is_system=True).first()
        assert role is not None, f"system role {role_code} not seeded for {organization}"
        return RoleAssignmentService.assign(account=account, role=role, assigned_by=assigned_by)

    return _grant


# Re-export the system role code constants so test files can import them locally.
OWNER = SystemRoleCode.OWNER
ADMIN = SystemRoleCode.ADMIN
MEMBER = SystemRoleCode.MEMBER
VIEWER = SystemRoleCode.VIEWER
