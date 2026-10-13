"""Write operations for projects + tasks."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import TYPE_CHECKING, Any

from django.db import transaction

from accounts.selectors import AccountSelectors
from core.exceptions import APIServiceError
from projects.constants import TERMINAL_TASK_STATUSES
from projects.exceptions import ProjectError, TaskError
from projects.models.project import Project
from projects.models.task import Task
from projects.policies import TaskPolicy
from projects.selectors import ProjectSelectors

if TYPE_CHECKING:
    from accounts.models.user import User
    from tenants.models.organization import Organization


class ProjectService:
    @staticmethod
    @transaction.atomic
    def create_project(
        *,
        organization: Organization,
        name: str,
        description: str,
        status: str,
        actor: User,
    ) -> Project:
        return Project.objects.create(
            organization=organization,
            name=name,
            description=description,
            status=status,
            created_by=actor,
            modified_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def update_project(
        *,
        project: Project,
        actor: User,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> Project:
        changed: list[str] = []
        if name is not None and name != project.name:
            project.name = name
            changed.append("name")
        if description is not None and description != project.description:
            project.description = description
            changed.append("description")
        if status is not None and status != project.status:
            project.status = status
            changed.append("status")
        if changed:
            project.modified_by = actor
            project.save(update_fields=[*changed, "modified_by", "modified_at"])
        return project

    @staticmethod
    @transaction.atomic
    def delete_project(*, project: Project, actor: User) -> None:
        project.delete(deleted_by=actor)


class TaskService:
    @staticmethod
    @transaction.atomic
    def create_task(
        *,
        organization: Organization,
        actor: User,
        project_id: uuid.UUID,
        title: str,
        description: str,
        status: str,
        assignee_id: uuid.UUID | None,
        due_date: _dt.date | None,
    ) -> Task:
        project = ProjectSelectors.get_by_public_id(organization, project_id)
        if project is None:
            raise APIServiceError(
                error_code=TaskError.ProjectRequired,
                status_code=400,
            )

        assignee = _resolve_assignee(organization, assignee_id)

        return Task.objects.create(
            organization=organization,
            project=project,
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
            created_by=actor,
            modified_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def update_task(
        *,
        task: Task,
        actor: User,
        data: dict[str, Any],
    ) -> Task:
        # Policy: only the assignee or an Owner/Admin may transition into a
        # terminal status. Fires only when `status` is being changed AND the
        # new value is terminal AND it's different from the current status.
        new_status = data.get("status")
        if new_status is not None and new_status in TERMINAL_TASK_STATUSES and new_status != task.status:
            account = AccountSelectors.get_by_user_and_organization(actor, task.organization)
            if account is None or not TaskPolicy.can_close(task, account):
                raise APIServiceError(
                    error_code=TaskError.NotAllowedToClose,
                    status_code=403,
                )

        changed: list[str] = []
        if "title" in data and data["title"] != task.title:
            task.title = data["title"]
            changed.append("title")
        if "description" in data and data["description"] != task.description:
            task.description = data["description"]
            changed.append("description")
        if "status" in data and data["status"] != task.status:
            task.status = data["status"]
            changed.append("status")
        if "due_date" in data and data["due_date"] != task.due_date:
            task.due_date = data["due_date"]
            changed.append("due_date")
        if "assignee_id" in data:
            new_assignee = _resolve_assignee(task.organization, data["assignee_id"])
            if (new_assignee.id if new_assignee else None) != task.assignee_id:
                task.assignee = new_assignee
                changed.append("assignee")
        if changed:
            task.modified_by = actor
            task.save(update_fields=[*changed, "modified_by", "modified_at"])
        return task

    @staticmethod
    @transaction.atomic
    def delete_task(*, task: Task, actor: User) -> None:
        task.delete(deleted_by=actor)


def _resolve_assignee(organization: Organization, assignee_id: uuid.UUID | None):
    """None → unassign. UUID → must point to an account on `organization`."""
    if assignee_id is None:
        return None

    from accounts.models.account import Account

    account = Account.records.filter(public_id=assignee_id, organization=organization).first()
    if account is None:
        raise APIServiceError(
            error_code=TaskError.AssigneeNotInOrganization,
            status_code=400,
        )
    return account


# Re-export the ProjectError not-found so views can raise it on 404.
__all__ = ["ProjectService", "TaskService", "ProjectError"]
