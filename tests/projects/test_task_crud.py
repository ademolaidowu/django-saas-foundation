"""Task CRUD endpoints."""

from __future__ import annotations

import pytest

from projects.constants import TaskStatus
from projects.models.task import Task

TASKS_URL = "/api/tasks/"


@pytest.mark.django_db
class TestTaskCrud:
    def test_create_task(self, owner_client, project_factory):
        client, user, _, alpha = owner_client
        project = project_factory(organization=alpha, actor=user)

        response = client.post(
            TASKS_URL,
            {
                "project_id": str(project.public_id),
                "title": "First task",
                "status": "todo",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        body = response.json()["data"]
        assert body["title"] == "First task"
        assert body["project"]["id"] == str(project.public_id)

    def test_cannot_create_task_on_another_orgs_project(self, owner_client, project_factory, two_orgs):
        client, user, _, _ = owner_client
        _, bravo = two_orgs
        bravo_project = project_factory(organization=bravo, actor=user)

        response = client.post(
            TASKS_URL,
            {
                "project_id": str(bravo_project.public_id),
                "title": "Nope",
                "status": "todo",
            },
            format="json",
        )
        # Project is not visible under Alpha scope → service returns ProjectRequired (400).
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "task_0002"

    def test_filter_by_project(self, owner_client, project_factory, task_factory):
        client, user, _, alpha = owner_client
        p1 = project_factory(organization=alpha, actor=user, name="P1")
        p2 = project_factory(organization=alpha, actor=user, name="P2")
        task_factory(project=p1, actor=user, title="t1")
        task_factory(project=p2, actor=user, title="t2")

        response = client.get(f"{TASKS_URL}?project={p1.public_id}")
        titles = [t["title"] for t in response.json()["data"]]
        assert titles == ["t1"]

    def test_filter_by_status(self, owner_client, project_factory, task_factory):
        client, user, _, alpha = owner_client
        project = project_factory(organization=alpha, actor=user)
        task_factory(project=project, actor=user, title="done one", status=TaskStatus.DONE)
        task_factory(project=project, actor=user, title="in flight", status=TaskStatus.IN_PROGRESS)

        response = client.get(f"{TASKS_URL}?status=in_progress")
        titles = [t["title"] for t in response.json()["data"]]
        assert titles == ["in flight"]

    def test_retrieve_update_delete_task(self, owner_client, project_factory, task_factory):
        client, user, _, alpha = owner_client
        project = project_factory(organization=alpha, actor=user)
        task = task_factory(project=project, actor=user, title="Edit")

        assert client.get(f"{TASKS_URL}{task.public_id}/").status_code == 200

        patched = client.patch(
            f"{TASKS_URL}{task.public_id}/",
            {"title": "Renamed", "status": "in_progress"},
            format="json",
        )
        assert patched.status_code == 200
        assert patched.json()["data"]["title"] == "Renamed"
        assert patched.json()["data"]["status"] == "in_progress"

        assert client.delete(f"{TASKS_URL}{task.public_id}/").status_code == 204
        assert not Task.records.for_organization(alpha).filter(pk=task.pk).exists()

    def test_assignee_must_belong_to_organization(
        self, owner_client, project_factory, user_factory, account_factory, two_orgs
    ):
        client, user, _, alpha = owner_client
        _, bravo = two_orgs
        bravo_user = user_factory(email="bu@example.com")
        bravo_account = account_factory(user=bravo_user, organization=bravo)
        project = project_factory(organization=alpha, actor=user)

        response = client.post(
            TASKS_URL,
            {
                "project_id": str(project.public_id),
                "title": "Mismatched",
                "assignee_id": str(bravo_account.public_id),
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "task_0003"
