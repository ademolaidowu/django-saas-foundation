"""Project CRUD endpoints."""

from __future__ import annotations

import pytest

from projects.constants import ProjectStatus
from projects.models.project import Project

PROJECTS_URL = "/api/projects/"


@pytest.mark.django_db
class TestProjectCrud:
    def test_create_as_owner(self, owner_client):
        client, _, _, _ = owner_client
        response = client.post(
            PROJECTS_URL,
            {"name": "MVP", "description": "ship it", "status": "active"},
            format="json",
        )
        assert response.status_code == 201, response.content
        body = response.json()["data"]
        assert body["name"] == "MVP"
        assert body["status"] == "active"

    def test_viewer_cannot_create(self, authed_client, seed_system_roles, grant_role, two_orgs):
        client, user, account = authed_client
        alpha, _ = two_orgs
        seed_system_roles(alpha, user)
        grant_role(account=account, role_code="viewer", assigned_by=user)

        response = client.post(
            PROJECTS_URL,
            {"name": "Nope", "status": "active"},
            format="json",
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "access_0001"

    def test_list_returns_only_my_org(self, owner_client, project_factory, two_orgs):
        client, user, _, alpha = owner_client
        _, bravo = two_orgs
        project_factory(organization=alpha, actor=user, name="Mine")
        project_factory(organization=bravo, actor=user, name="Theirs")

        response = client.get(PROJECTS_URL)
        names = [p["name"] for p in response.json()["data"]]
        assert "Mine" in names
        assert "Theirs" not in names

    def test_status_filter(self, owner_client, project_factory):
        client, user, _, alpha = owner_client
        project_factory(organization=alpha, actor=user, name="A", status=ProjectStatus.ACTIVE)
        project_factory(organization=alpha, actor=user, name="B", status=ProjectStatus.PLANNING)

        response = client.get(f"{PROJECTS_URL}?status=planning")
        names = [p["name"] for p in response.json()["data"]]
        assert names == ["B"]

    def test_retrieve_update_delete(self, owner_client, project_factory):
        client, user, _, alpha = owner_client
        project = project_factory(organization=alpha, actor=user, name="Edit me")

        # Retrieve
        detail = client.get(f"{PROJECTS_URL}{project.public_id}/")
        assert detail.status_code == 200

        # Update
        patched = client.patch(
            f"{PROJECTS_URL}{project.public_id}/",
            {"name": "Renamed", "status": "on_hold"},
            format="json",
        )
        assert patched.status_code == 200
        assert patched.json()["data"]["name"] == "Renamed"

        # Delete
        deleted = client.delete(f"{PROJECTS_URL}{project.public_id}/")
        assert deleted.status_code == 204
        assert not Project.records.for_organization(alpha).filter(pk=project.pk).exists()
