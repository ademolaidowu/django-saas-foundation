"""
Object-level authorization checks.

Phase 3 only ships the last-Owner invariant (enforced in
`RoleAssignmentService.revoke`). Per-object policies for the domain layer
(Project/Task — "only the assignee or an admin can close a task") land in
Phase 4 and will live here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from access.constants import SystemRoleCode
from access.selectors import RoleAssignmentSelectors

if TYPE_CHECKING:
    from access.models.assignment import RoleAssignment


class RoleAssignmentPolicy:
    @staticmethod
    def would_strand_organization_without_owner(assignment: RoleAssignment) -> bool:
        """
        True if revoking (or deactivating / soft-deleting) `assignment` would
        leave the organization with zero active Owner assignments.
        """
        if assignment.role.code != SystemRoleCode.OWNER or not assignment.role.is_system:
            return False
        remaining = RoleAssignmentSelectors.count_active_owners(assignment.role.organization) - 1
        return remaining <= 0
