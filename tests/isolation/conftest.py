"""
Fixtures for the cross-org isolation matrix.

`two_orgs_with_rbac` builds Alpha + Bravo, seeds the four system roles on each,
grants Owner to Alice on Alpha, logs her in via the real auth endpoint, and
populates Bravo with one-of-every-tenant-scoped-resource so the matrix has
something to probe from the wrong side.

`ENDPOINT_SPECS` is the registry — add a new tenant-scoped resource to this
tuple and every operation (list/retrieve/update/delete/history) gets covered
in `test_endpoint_isolation.py` automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from access.constants import SystemRoleCode
from access.services import RoleAssignmentService, RoleService
from projects.constants import ProjectStatus, TaskStatus
from projects.models.project import Project
from projects.models.task import Task

PASSWORD = "testpassword123"


@dataclass(frozen=True)
class EndpointSpec:
    name: str
    list_url: str
    detail_url_tpl: str  # e.g. "/api/projects/{public_id}/"
    bravo_key: str  # key under `bravo` dict pointing at the resource
    has_list: bool = True
    has_retrieve: bool = True
    has_update: bool = True
    has_delete: bool = True
    has_history: bool = False
    update_payload: dict[str, Any] = field(default_factory=lambda: {"name": "pwned"})


ENDPOINT_SPECS: tuple[EndpointSpec, ...] = (
    EndpointSpec(
        name="projects",
        list_url="/api/projects/",
        detail_url_tpl="/api/projects/{public_id}/",
        bravo_key="project",
        has_history=True,
        update_payload={"name": "pwned"},
    ),
    EndpointSpec(
        name="tasks",
        list_url="/api/tasks/",
        detail_url_tpl="/api/tasks/{public_id}/",
        bravo_key="task",
        update_payload={"title": "pwned"},
    ),
    EndpointSpec(
        name="roles",
        list_url="/api/access/roles/",
        detail_url_tpl="/api/access/roles/{public_id}/",
        bravo_key="role",
        update_payload={"name": "pwned"},
    ),
    EndpointSpec(
        name="role-assignments",
        list_url="",  # no list endpoint for role-assignments
        detail_url_tpl="/api/access/role-assignments/{public_id}/",
        bravo_key="role_assignment",
        has_list=False,
        has_retrieve=False,
        has_update=False,
        has_delete=True,
    ),
)


@pytest.fixture
def two_orgs_with_rbac(
    db,
    api_client,
    user_factory,
    account_factory,
    two_orgs,
):
    """Build Alpha + Bravo with system roles; Alice is Owner on Alpha, logged in."""
    alpha, bravo = two_orgs

    alice = user_factory(email="alice@acme.com")
    alice_alpha = account_factory(user=alice, organization=alpha, is_primary=True)

    # Seed roles on both orgs
    alpha_roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=alice)
    bravo_user = user_factory(email="bravo@globex.com")
    bravo_account = account_factory(user=bravo_user, organization=bravo, is_primary=True)
    bravo_roles = RoleService.create_system_roles_for_organization(organization=bravo, created_by=bravo_user)

    RoleAssignmentService.assign(
        account=alice_alpha,
        role=alpha_roles[SystemRoleCode.OWNER],
        assigned_by=alice,
    )
    RoleAssignmentService.assign(
        account=bravo_account,
        role=bravo_roles[SystemRoleCode.OWNER],
        assigned_by=bravo_user,
    )

    # Populate Bravo with one of each resource
    bravo_project = Project.objects.create(
        organization=bravo,
        name="Bravo Secret",
        description="",
        status=ProjectStatus.ACTIVE,
        created_by=bravo_user,
        modified_by=bravo_user,
    )
    bravo_task = Task.objects.create(
        organization=bravo,
        project=bravo_project,
        title="Bravo task",
        status=TaskStatus.TODO,
        created_by=bravo_user,
        modified_by=bravo_user,
    )
    bravo_role = RoleService.create_role(
        organization=bravo,
        name="Bravo Custom",
        description="",
        permission_codes=["projects.read"],
        created_by=bravo_user,
    )
    # Second Bravo account to be the target of an assignment
    second_bravo_user = user_factory(email="second-bravo@globex.com")
    second_bravo_account = account_factory(user=second_bravo_user, organization=bravo, is_primary=False)
    bravo_assignment = RoleAssignmentService.assign(
        account=second_bravo_account,
        role=bravo_role,
        assigned_by=bravo_user,
    )

    # Alice logs in — cookie is set on the client
    r = api_client.post(
        "/api/auth/login/",
        {"email": alice.email, "password": PASSWORD},
        format="json",
    )
    assert r.status_code == 200, r.content

    return {
        "client": api_client,
        "alice": alice,
        "alpha": alpha,
        "bravo": bravo,
        "bravo_user": bravo_user,
        "bravo_fixtures": {
            "project": bravo_project,
            "task": bravo_task,
            "role": bravo_role,
            "role_assignment": bravo_assignment,
        },
    }
