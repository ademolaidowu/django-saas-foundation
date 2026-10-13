"""Project — the top-level domain unit, tenant-scoped and audited."""

from __future__ import annotations

from django.db import models
from simple_history.models import HistoricalRecords

from core.models.base import AuditTrailMixin
from core.models.tenancy import TenantScopedModel
from projects.constants import ProjectStatus


class Project(AuditTrailMixin, TenantScopedModel):
    class Meta:
        db_table = "projects"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "name"]),
        ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=ProjectStatus.max_name_length(),
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE,
    )

    history = HistoricalRecords(table_name="projects_history", excluded_fields=["modified_at"])

    def __str__(self) -> str:
        return self.name
