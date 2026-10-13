"""Fixtures for projects tests."""

from __future__ import annotations

import pytest

from access.constants import SystemRoleCode
from access.models.role import Role
from access.services import RoleAssignmentService, RoleService
from projects.constants import ProjectStatus, TaskStatus
from projects.models.project import Project
from projects.models.task import Task


@pytest.fixture
def project_factory(db):
    def _make(
        *,
        organization,
        actor,
        name: str = "Sample Project",
        description: str = "",
        status: str = ProjectStatus.ACTIVE,
    ) -> Project:
        return Project.objects.create(
            organization=organization,
            name=name,
            description=description,
            status=status,
            created_by=actor,
            modified_by=actor,
        )

    return _make


@pytest.fixture
def task_factory(db):
    def _make(
        *,
        project,
        actor,
        title: str = "Sample Task",
        description: str = "",
        status: str = TaskStatus.TODO,
        assignee=None,
        due_date=None,
    ) -> Task:
        return Task.objects.create(
            organization=project.organization,
            project=project,
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
            created_by=actor,
            modified_by=actor,
        )

    return _make


@pytest.fixture
def seed_system_roles(db):
    """Seed the four system roles for a given organization."""

    def _seed(organization, actor):
        return RoleService.create_system_roles_for_organization(organization=organization, created_by=actor)

    return _seed


@pytest.fixture
def grant_role(db):
    """Assign a system role (by code) to an account on its organization."""

    def _grant(*, account, role_code: str, assigned_by):
        role = Role.records.for_organization(account.organization).filter(code=role_code, is_system=True).first()
        assert role is not None, f"system role {role_code} not seeded for {account.organization}"
        return RoleAssignmentService.assign(account=account, role=role, assigned_by=assigned_by)

    return _grant


@pytest.fixture
def owner_client(authed_client, seed_system_roles, grant_role, two_orgs):
    """A logged-in client whose account holds the Owner role on Alpha."""
    client, user, account = authed_client
    alpha, _ = two_orgs
    seed_system_roles(alpha, user)
    grant_role(account=account, role_code=SystemRoleCode.OWNER, assigned_by=user)
    return client, user, account, alpha


@pytest.fixture
def member_client(authed_client, seed_system_roles, grant_role, two_orgs):
    """A logged-in client whose account holds the Member role on Alpha."""
    client, user, account = authed_client
    alpha, _ = two_orgs
    seed_system_roles(alpha, user)
    grant_role(account=account, role_code=SystemRoleCode.MEMBER, assigned_by=user)
    return client, user, account, alpha
