"""Direct unit tests for projects selectors."""

from __future__ import annotations

import uuid

import pytest

from projects.constants import ProjectStatus, TaskStatus
from projects.selectors import ProjectSelectors, TaskSelectors


@pytest.mark.django_db
class TestProjectSelectors:
    def test_list_scoped_and_status_filter(self, user_factory, project_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        project_factory(organization=alpha, actor=user, name="A", status=ProjectStatus.ACTIVE)
        project_factory(organization=alpha, actor=user, name="B", status=ProjectStatus.PLANNING)
        project_factory(organization=bravo, actor=user, name="C", status=ProjectStatus.ACTIVE)

        active = ProjectSelectors.list_for_organization(alpha, status=ProjectStatus.ACTIVE)
        assert [p.name for p in active] == ["A"]

        all_alpha = ProjectSelectors.list_for_organization(alpha)
        assert sorted(p.name for p in all_alpha) == ["A", "B"]

    def test_get_by_public_id_miss_returns_none(self, two_orgs):
        alpha, _ = two_orgs
        assert ProjectSelectors.get_by_public_id(alpha, uuid.uuid4()) is None

    def test_get_by_public_id_wrong_org_returns_none(self, user_factory, project_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        bravo_project = project_factory(organization=bravo, actor=user, name="B")
        assert ProjectSelectors.get_by_public_id(alpha, bravo_project.public_id) is None


@pytest.mark.django_db
class TestTaskSelectors:
    def test_filters_combine(self, user_factory, account_factory, project_factory, task_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha, is_primary=True)
        p1 = project_factory(organization=alpha, actor=user, name="P1")
        p2 = project_factory(organization=alpha, actor=user, name="P2")
        task_factory(project=p1, actor=user, title="t1", status=TaskStatus.TODO)
        task_factory(project=p1, actor=user, title="t2", status=TaskStatus.DONE, assignee=account)
        task_factory(project=p2, actor=user, title="t3", status=TaskStatus.TODO)

        # Filter: project=p1
        p1_tasks = TaskSelectors.list_for_organization(alpha, project_id=p1.public_id)
        assert sorted(t.title for t in p1_tasks) == ["t1", "t2"]

        # Filter: status=todo + project=p1
        todo_p1 = TaskSelectors.list_for_organization(alpha, project_id=p1.public_id, status=TaskStatus.TODO)
        assert [t.title for t in todo_p1] == ["t1"]

        # Filter: assignee
        assigned = TaskSelectors.list_for_organization(alpha, assignee_id=account.public_id)
        assert [t.title for t in assigned] == ["t2"]
