"""
Object-level checks for the projects app.

`TaskPolicy.can_close` is the headline example — a transition into a terminal
status (`done` or `cancelled`) is only allowed by the assignee or by someone
holding an Owner/Admin system role. Non-terminal transitions stay under
the `tasks.update` permission alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from access.constants import SystemRoleCode

if TYPE_CHECKING:
    from accounts.models.account import Account
    from projects.models.task import Task


class TaskPolicy:
    @staticmethod
    def can_close(task: Task, account: Account) -> bool:
        if task.assignee_id == account.id:
            return True
        return account.role_assignments.filter(
            is_active=True,
            deleted_at__isnull=True,
            role__is_system=True,
            role__code__in=(SystemRoleCode.OWNER, SystemRoleCode.ADMIN),
        ).exists()
