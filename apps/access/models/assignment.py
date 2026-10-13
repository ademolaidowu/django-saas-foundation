"""Account ↔ Role binding."""

from __future__ import annotations

from django.db import models
from django.db.models import Q
from simple_history.models import HistoricalRecords

from core.models.base import AuditTrailMixin, BaseModel


class RoleAssignment(AuditTrailMixin, BaseModel):
    """
    Links an `accounts.Account` to an `access.Role`.

    Not a `TenantScopedModel` directly — but the invariant
    `account.organization_id == role.organization_id` is checked in
    `RoleAssignmentService.assign`. Enforcing cross-FK equality at the DB
    level is awkward; the service layer owns it.

    `is_active=False` is used to deactivate without destroying history.
    """

    class Meta:
        db_table = "role_assignments"
        constraints = [
            models.UniqueConstraint(
                fields=["account", "role"],
                condition=Q(deleted_at__isnull=True),
                name="unique_account_role",
            ),
        ]
        indexes = [
            models.Index(fields=["account", "is_active"]),
        ]

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        "access.Role",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords(
        table_name="role_assignments_history",
        excluded_fields=["modified_at"],
    )

    def __str__(self) -> str:
        return f"RoleAssignment({self.account_id} → {self.role_id})"
