"""
Single source of truth for permission codes and system-role → permission splits.

Permissions are keyed by colon-separated code (`<module>:<action>`). `seed_rbac`
upserts these into the `access.Permission` table. System roles are
per-organization convenience defaults seeded by
`RoleService.create_system_roles_for_organization`.

Phase 4 placeholders for `projects:*` and `tasks:*` are declared here so that
the Member/Viewer splits are complete out of the box. When Phase 4 lands, the
views just use codes that already exist.
"""

from __future__ import annotations

from dataclasses import dataclass

from access.constants import SystemRoleCode


@dataclass(frozen=True)
class PermissionDef:
    code: str
    description: str


@dataclass(frozen=True)
class SystemRoleDef:
    code: str
    name: str
    description: str
    permission_codes: tuple[str, ...]


PERMISSIONS: tuple[PermissionDef, ...] = (
    # access
    PermissionDef("roles:read", "List and view roles."),
    PermissionDef("roles:create", "Create custom roles."),
    PermissionDef("roles:update", "Rename or edit custom roles."),
    PermissionDef("roles:delete", "Delete custom roles."),
    PermissionDef("role_assignments:create", "Assign roles to accounts."),
    PermissionDef("role_assignments:delete", "Revoke role assignments."),
    PermissionDef("permissions:read", "List all permission codes."),
    PermissionDef("accounts:read", "View members of the organization."),
    # organization (reserved for future billing / destroy)
    PermissionDef("organization:manage", "Owner-only organization-level operations."),
    # Phase 4 placeholders — declared now so system-role splits are complete.
    PermissionDef("projects:read", "View projects."),
    PermissionDef("projects:create", "Create projects."),
    PermissionDef("projects:update", "Edit projects."),
    PermissionDef("projects:delete", "Delete projects."),
    PermissionDef("tasks:read", "View tasks."),
    PermissionDef("tasks:create", "Create tasks."),
    PermissionDef("tasks:update", "Edit tasks (assign, change status, due date)."),
    PermissionDef("tasks:delete", "Delete tasks."),
)

ALL_CODES: tuple[str, ...] = tuple(p.code for p in PERMISSIONS)
READ_CODES: tuple[str, ...] = tuple(c for c in ALL_CODES if c.endswith(":read"))
ADMIN_CODES: tuple[str, ...] = tuple(c for c in ALL_CODES if c != "organization:manage")
MEMBER_CODES: tuple[str, ...] = tuple(
    c for c in ALL_CODES if c.startswith(("projects:", "tasks:")) or c == "accounts:read"
)


SYSTEM_ROLES: tuple[SystemRoleDef, ...] = (
    SystemRoleDef(
        code=SystemRoleCode.OWNER,
        name="Owner",
        description="Full control over the organization.",
        permission_codes=ALL_CODES,
    ),
    SystemRoleDef(
        code=SystemRoleCode.ADMIN,
        name="Admin",
        description="Full access except organization-level management (billing, destroy).",
        permission_codes=ADMIN_CODES,
    ),
    SystemRoleDef(
        code=SystemRoleCode.MEMBER,
        name="Member",
        description="Create and manage domain data (projects and tasks).",
        permission_codes=MEMBER_CODES,
    ),
    SystemRoleDef(
        code=SystemRoleCode.VIEWER,
        name="Viewer",
        description="Read-only access.",
        permission_codes=READ_CODES,
    ),
)
