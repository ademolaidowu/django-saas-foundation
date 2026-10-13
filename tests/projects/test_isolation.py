"""Cross-tenant isolation for project + task endpoints — Phase 5 preview."""

from __future__ import annotations

import pytest

PROJECTS_URL = "/api/projects/"
TASKS_URL = "/api/tasks/"


@pytest.mark.django_db
class TestProjectIsolation:
    def test_retrieve_cross_tenant_returns_404(self, owner_client, project_factory, two_orgs, user_factory):
        client, user, _, _ = owner_client
        _, bravo = two_orgs
        bravo_project = project_factory(organization=bravo, actor=user, name="Hidden")

        r = client.get(f"{PROJECTS_URL}{bravo_project.public_id}/")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "project_0001"

    def test_update_cross_tenant_returns_404(self, owner_client, project_factory, two_orgs, user_factory):
        client, user, _, _ = owner_client
        _, bravo = two_orgs
        bravo_project = project_factory(organization=bravo, actor=user)

        r = client.patch(
            f"{PROJECTS_URL}{bravo_project.public_id}/",
            {"name": "Pwned"},
            format="json",
        )
        assert r.status_code == 404

    def test_delete_cross_tenant_returns_404(self, owner_client, project_factory, two_orgs, user_factory):
        client, user, _, _ = owner_client
        _, bravo = two_orgs
        bravo_project = project_factory(organization=bravo, actor=user)

        r = client.delete(f"{PROJECTS_URL}{bravo_project.public_id}/")
        assert r.status_code == 404

    def test_list_excludes_other_orgs(self, owner_client, project_factory, two_orgs, user_factory):
        client, user, _, alpha = owner_client
        _, bravo = two_orgs
        project_factory(organization=alpha, actor=user, name="Mine")
        project_factory(organization=bravo, actor=user, name="Theirs")

        r = client.get(PROJECTS_URL)
        names = [p["name"] for p in r.json()["data"]]
        assert "Mine" in names
        assert "Theirs" not in names


@pytest.mark.django_db
class TestTaskIsolation:
    def test_retrieve_cross_tenant_returns_404(
        self, owner_client, project_factory, task_factory, two_orgs, user_factory
    ):
        client, user, _, _ = owner_client
        _, bravo = two_orgs
        bravo_project = project_factory(organization=bravo, actor=user)
        bravo_task = task_factory(project=bravo_project, actor=user, title="Hidden")

        r = client.get(f"{TASKS_URL}{bravo_task.public_id}/")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "task_0001"

    def test_list_excludes_other_orgs(self, owner_client, project_factory, task_factory, two_orgs, user_factory):
        client, user, _, alpha = owner_client
        _, bravo = two_orgs
        alpha_project = project_factory(organization=alpha, actor=user)
        bravo_project = project_factory(organization=bravo, actor=user)
        task_factory(project=alpha_project, actor=user, title="Mine")
        task_factory(project=bravo_project, actor=user, title="Theirs")

        r = client.get(TASKS_URL)
        titles = [t["title"] for t in r.json()["data"]]
        assert "Mine" in titles
        assert "Theirs" not in titles
