"""
Role × endpoint permission matrix.

Every seeded role has a known set of allowed and denied actions. This grid
parametrises `(role_code, endpoint_key)` against the API and asserts that
each cell either succeeds or returns 403 (`access_0001`) as expected.

Keeps the four role definitions honest — if someone edits
`apps/access/registry.py` and shifts a permission into the wrong system role,
this suite fails loudly instead of letting the drift ship.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from access.constants import SystemRoleCode
from access.services import RoleAssignmentService, RoleService

PASSWORD = "testpassword123"

ALLOW = "allow"
DENY = "deny"


# (method, url, body) → tested per role
ENDPOINTS: dict[str, tuple[str, str, dict | None]] = {
    "permissions:list": ("GET", "/api/access/permissions/", None),
    "roles:list": ("GET", "/api/access/roles/", None),
    "roles:create": (
        "POST",
        "/api/access/roles/",
        {"name": "Scratch", "permission_codes": []},
    ),
    "projects:list": ("GET", "/api/projects/", None),
    "projects:create": (
        "POST",
        "/api/projects/",
        {"name": "P", "status": "active"},
    ),
    "tasks:list": ("GET", "/api/tasks/", None),
}

MATRIX: dict[str, dict[str, str]] = {
    SystemRoleCode.OWNER: {
        "permissions:list": ALLOW,
        "roles:list": ALLOW,
        "roles:create": ALLOW,
        "projects:list": ALLOW,
        "projects:create": ALLOW,
        "tasks:list": ALLOW,
    },
    SystemRoleCode.ADMIN: {
        "permissions:list": ALLOW,
        "roles:list": ALLOW,
        "roles:create": ALLOW,
        "projects:list": ALLOW,
        "projects:create": ALLOW,
        "tasks:list": ALLOW,
    },
    SystemRoleCode.MEMBER: {
        "permissions:list": DENY,
        "roles:list": DENY,
        "roles:create": DENY,
        "projects:list": ALLOW,
        "projects:create": ALLOW,
        "tasks:list": ALLOW,
    },
    SystemRoleCode.VIEWER: {
        "permissions:list": ALLOW,  # viewer has all *:read incl. permissions:read
        "roles:list": ALLOW,
        "roles:create": DENY,
        "projects:list": ALLOW,
        "projects:create": DENY,
        "tasks:list": ALLOW,
    },
}

_CASES = [
    (role_code, endpoint_key, expected)
    for role_code, cells in MATRIX.items()
    for endpoint_key, expected in cells.items()
]


@pytest.fixture
def role_login_factory(db, user_factory, account_factory, two_orgs):
    """Return a function that creates a user with the given role and returns an APIClient logged in as them."""

    def _make(role_code: str) -> APIClient:
        alpha, _ = two_orgs
        # Email is role-prefixed so the fixture is reusable across the matrix.
        user = user_factory(email=f"{role_code}@example.com")
        account = account_factory(user=user, organization=alpha, is_primary=True)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        RoleAssignmentService.assign(account=account, role=roles[role_code], assigned_by=user)
        client = APIClient()
        r = client.post(
            "/api/auth/login/",
            {"email": user.email, "password": PASSWORD},
            format="json",
        )
        assert r.status_code == 200
        return client

    return _make


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role_code", "endpoint_key", "expected"),
    _CASES,
    ids=[f"{r}:{e}:{v}" for r, e, v in _CASES],
)
class TestPermissionMatrix:
    def test_cell(self, role_code, endpoint_key, expected, role_login_factory):
        client = role_login_factory(role_code)
        method, url, body = ENDPOINTS[endpoint_key]
        func = getattr(client, method.lower())
        response = func(url, body, format="json") if body is not None else func(url)

        if expected == ALLOW:
            assert response.status_code in (200, 201), (
                f"{role_code} {method} {url} → got {response.status_code} ({response.content!r})"
            )
        else:
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "access_0001"


@pytest.mark.django_db
class TestCustomRole:
    """Custom roles work — not just the four seeded ones."""

    def test_custom_role_grants_exactly_its_permissions(self, user_factory, account_factory, two_orgs, password):
        alpha, _ = two_orgs
        owner = user_factory(email="owner@example.com")
        owner_account = account_factory(user=owner, organization=alpha, is_primary=True)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=owner)
        RoleAssignmentService.assign(
            account=owner_account,
            role=roles[SystemRoleCode.OWNER],
            assigned_by=owner,
        )

        # Owner creates a bespoke "Readonly Projects" role
        readonly = RoleService.create_role(
            organization=alpha,
            name="Projects Readonly",
            description="",
            permission_codes=["projects:read", "tasks:read"],
            created_by=owner,
        )

        bob = user_factory(email="bob@example.com")
        bob_account = account_factory(user=bob, organization=alpha, is_primary=True)
        RoleAssignmentService.assign(account=bob_account, role=readonly, assigned_by=owner)

        client = APIClient()
        r = client.post(
            "/api/auth/login/",
            {"email": bob.email, "password": password},
            format="json",
        )
        assert r.status_code == 200

        # Allowed: list projects + tasks
        assert client.get("/api/projects/").status_code == 200
        assert client.get("/api/tasks/").status_code == 200

        # Denied: creating anything
        create = client.post(
            "/api/projects/",
            {"name": "Nope", "status": "active"},
            format="json",
        )
        assert create.status_code == 403
        assert create.json()["error"]["code"] == "access_0001"
