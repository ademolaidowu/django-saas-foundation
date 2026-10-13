"""Role and its through-table to Permission."""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.models.base import AuditTrailMixin, BaseModel
from core.models.tenancy import TenantScopedModel


class Role(AuditTrailMixin, TenantScopedModel):
    """
    A collection of permissions, scoped to one organization.

    `is_system=True` marks the four seeded roles (Owner/Admin/Member/Viewer).
    System roles cannot be renamed or deleted; their `code` identifies them
    for programmatic lookup (e.g. the last-Owner protection).
    """

    class Meta:
        db_table = "roles"
        ordering = ("-is_system", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=Q(code__isnull=False, deleted_at__isnull=True),
                name="unique_role_code_per_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_role_name_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "is_system"]),
        ]

    code = models.SlugField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(
        "access.Permission",
        through="access.RolePermission",
        related_name="roles",
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.organization_id})"


class RolePermission(BaseModel):
    """
    Explicit through-table so Phase 4's `simple_history` can track grants/revokes.
    No `AuditTrailMixin` — the parent `Role` already carries actor FKs; a per-row
    audit on grants would be visual noise.
    """

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                condition=Q(deleted_at__isnull=True),
                name="unique_role_permission",
            ),
        ]

    role = models.ForeignKey(
        "access.Role",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        "access.Permission",
        on_delete=models.CASCADE,
        related_name="+",
    )
