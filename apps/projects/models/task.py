"""Task — belongs to a Project; also carries its own `organization` for the tenant guard."""

from __future__ import annotations

from django.db import models
from simple_history.models import HistoricalRecords

from core.models.base import AuditTrailMixin
from core.models.tenancy import TenantScopedModel
from projects.constants import TaskStatus


class Task(AuditTrailMixin, TenantScopedModel):
    class Meta:
        db_table = "tasks"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["assignee"]),
        ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=TaskStatus.max_name_length(),
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
    )
    assignee = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True)

    history = HistoricalRecords(table_name="tasks_history", excluded_fields=["modified_at"])

    def __str__(self) -> str:
        return self.title
