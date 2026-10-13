"""Read-only lookups for projects + tasks."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db.models import QuerySet

from projects.models.project import Project
from projects.models.task import Task

if TYPE_CHECKING:
    from tenants.models.organization import Organization


class ProjectSelectors:
    @staticmethod
    def list_for_organization(
        organization: Organization,
        status: str | None = None,
    ) -> QuerySet[Project]:
        qs = Project.records.for_organization(organization)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    @staticmethod
    def get_by_public_id(
        organization: Organization,
        public_id: uuid.UUID,
    ) -> Project | None:
        return Project.records.for_organization(organization).filter(public_id=public_id).first()


class TaskSelectors:
    @staticmethod
    def list_for_organization(
        organization: Organization,
        *,
        status: str | None = None,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
    ) -> QuerySet[Task]:
        qs = Task.records.for_organization(organization).select_related("project", "assignee")
        if status:
            qs = qs.filter(status=status)
        if project_id:
            qs = qs.filter(project__public_id=project_id)
        if assignee_id:
            qs = qs.filter(assignee__public_id=assignee_id)
        return qs.order_by("-created_at")

    @staticmethod
    def get_by_public_id(
        organization: Organization,
        public_id: uuid.UUID,
    ) -> Task | None:
        return (
            Task.records.for_organization(organization)
            .filter(public_id=public_id)
            .select_related("project", "assignee")
            .first()
        )
