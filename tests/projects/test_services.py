"""Direct unit tests for projects services."""

from __future__ import annotations

import datetime as _dt

import pytest

from access.constants import SystemRoleCode
from access.services import RoleAssignmentService, RoleService
from core.exceptions import APIServiceError
from projects.constants import ProjectStatus, TaskStatus
from projects.exceptions import TaskError
from projects.models.project import Project
from projects.services import ProjectService, TaskService


@pytest.mark.django_db
class TestProjectService:
    def test_create_project(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="",
            status=ProjectStatus.ACTIVE,
            actor=user,
        )
        assert project.name == "P"
        assert project.created_by == user

    def test_update_project_no_changes_is_noop(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="d",
            status=ProjectStatus.ACTIVE,
            actor=user,
        )
        modified_before = project.modified_at
        # Pass identical values — no change should fire.
        ProjectService.update_project(
            project=project, actor=user, name="P", description="d", status=ProjectStatus.ACTIVE
        )
        project.refresh_from_db()
        assert project.modified_at == modified_before

    def test_update_project_partial_fields(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="",
            status=ProjectStatus.PLANNING,
            actor=user,
        )
        ProjectService.update_project(project=project, actor=user, status=ProjectStatus.ACTIVE)
        project.refresh_from_db()
        assert project.status == ProjectStatus.ACTIVE
        assert project.name == "P"

    def test_delete_project_soft_deletes(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="",
            status=ProjectStatus.ACTIVE,
            actor=user,
        )
        ProjectService.delete_project(project=project, actor=user)
        # Lives in `objects` (all rows) but not in `records` (alive-only)
        assert Project.objects.unsafe_all().filter(pk=project.pk).exists()
        assert not Project.records.for_organization(alpha).filter(pk=project.pk).exists()


@pytest.mark.django_db
class TestTaskService:
    def _setup_org_with_project(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account_factory(user=user, organization=alpha, is_primary=True)
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="",
            status=ProjectStatus.ACTIVE,
            actor=user,
        )
        return alpha, user, project

    def test_create_task_rejects_project_from_another_org(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        bravo_user = user_factory(email="b@example.com")
        bravo_project = ProjectService.create_project(
            organization=bravo,
            name="B",
            description="",
            status=ProjectStatus.ACTIVE,
            actor=bravo_user,
        )
        alpha_user = user_factory(email="a@example.com")
        with pytest.raises(APIServiceError) as exc:
            TaskService.create_task(
                organization=alpha,
                actor=alpha_user,
                project_id=bravo_project.public_id,
                title="t",
                description="",
                status=TaskStatus.TODO,
                assignee_id=None,
                due_date=None,
            )
        assert exc.value.error_code is TaskError.ProjectRequired

    def test_create_task_rejects_assignee_from_another_org(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        alpha_user = user_factory(email="a@example.com")
        account_factory(user=alpha_user, organization=alpha, is_primary=True)
        bravo_user = user_factory(email="b@example.com")
        bravo_account = account_factory(user=bravo_user, organization=bravo, is_primary=True)
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="",
            status=ProjectStatus.ACTIVE,
            actor=alpha_user,
        )
        with pytest.raises(APIServiceError) as exc:
            TaskService.create_task(
                organization=alpha,
                actor=alpha_user,
                project_id=project.public_id,
                title="t",
                description="",
                status=TaskStatus.TODO,
                assignee_id=bravo_account.public_id,
                due_date=None,
            )
        assert exc.value.error_code is TaskError.AssigneeNotInOrganization

    def test_create_task_unassigned_ok(self, user_factory, account_factory, two_orgs):
        alpha, user, project = self._setup_org_with_project(user_factory, account_factory, two_orgs)
        task = TaskService.create_task(
            organization=alpha,
            actor=user,
            project_id=project.public_id,
            title="t",
            description="",
            status=TaskStatus.TODO,
            assignee_id=None,
            due_date=_dt.date(2026, 6, 1),
        )
        assert task.assignee is None
        assert task.due_date == _dt.date(2026, 6, 1)

    def test_update_task_close_requires_assignee_or_admin(self, user_factory, account_factory, two_orgs):
        alpha, user, project = self._setup_org_with_project(user_factory, account_factory, two_orgs)
        task = TaskService.create_task(
            organization=alpha,
            actor=user,
            project_id=project.public_id,
            title="t",
            description="",
            status=TaskStatus.TODO,
            assignee_id=None,
            due_date=None,
        )
        # user has no roles → policy denies the close
        with pytest.raises(APIServiceError) as exc:
            TaskService.update_task(task=task, actor=user, data={"status": TaskStatus.DONE})
        assert exc.value.error_code is TaskError.NotAllowedToClose

    def test_update_task_close_as_owner_allowed(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha, is_primary=True)
        roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=user)
        RoleAssignmentService.assign(account=account, role=roles[SystemRoleCode.OWNER], assigned_by=user)
        project = ProjectService.create_project(
            organization=alpha,
            name="P",
            description="",
            status=ProjectStatus.ACTIVE,
            actor=user,
        )
        task = TaskService.create_task(
            organization=alpha,
            actor=user,
            project_id=project.public_id,
            title="t",
            description="",
            status=TaskStatus.TODO,
            assignee_id=None,
            due_date=None,
        )
        task = TaskService.update_task(task=task, actor=user, data={"status": TaskStatus.DONE})
        assert task.status == TaskStatus.DONE

    def test_update_task_non_terminal_bypasses_close_policy(self, user_factory, account_factory, two_orgs):
        alpha, user, project = self._setup_org_with_project(user_factory, account_factory, two_orgs)
        task = TaskService.create_task(
            organization=alpha,
            actor=user,
            project_id=project.public_id,
            title="t",
            description="",
            status=TaskStatus.TODO,
            assignee_id=None,
            due_date=None,
        )
        # User has no roles — but moving to IN_PROGRESS is non-terminal, so OK.
        task = TaskService.update_task(task=task, actor=user, data={"status": TaskStatus.IN_PROGRESS})
        assert task.status == TaskStatus.IN_PROGRESS

    def test_update_task_no_change_is_noop(self, user_factory, account_factory, two_orgs):
        alpha, user, project = self._setup_org_with_project(user_factory, account_factory, two_orgs)
        task = TaskService.create_task(
            organization=alpha,
            actor=user,
            project_id=project.public_id,
            title="t",
            description="",
            status=TaskStatus.TODO,
            assignee_id=None,
            due_date=None,
        )
        before = task.modified_at
        TaskService.update_task(task=task, actor=user, data={"title": "t"})
        task.refresh_from_db()
        assert task.modified_at == before
