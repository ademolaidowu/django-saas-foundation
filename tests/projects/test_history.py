"""History endpoint + acting-user capture via `HistoryRequestMiddleware`."""

from __future__ import annotations

import pytest

PROJECTS_URL = "/api/projects/"


@pytest.mark.django_db
class TestProjectHistory:
    def test_create_generates_plus_record(self, owner_client, project_factory):
        client, user, _, alpha = owner_client

        # Trigger through the API so the request middleware captures the user.
        response = client.post(
            PROJECTS_URL,
            {"name": "H1", "description": "orig", "status": "planning"},
            format="json",
        )
        project_id = response.json()["data"]["id"]

        history_resp = client.get(f"{PROJECTS_URL}{project_id}/history/")
        assert history_resp.status_code == 200

        records = history_resp.json()["data"]
        assert len(records) == 1
        record = records[0]
        assert record["history_type"] == "+"
        assert record["changed_fields"] is None
        assert record["history_user"]["email"] == user.email

    def test_update_generates_tilde_record_with_diff(self, owner_client, project_factory):
        client, _, _, _ = owner_client
        created = client.post(
            PROJECTS_URL,
            {"name": "H2", "description": "orig", "status": "planning"},
            format="json",
        ).json()["data"]

        client.patch(
            f"{PROJECTS_URL}{created['id']}/",
            {"status": "active", "description": "updated"},
            format="json",
        )

        records = client.get(f"{PROJECTS_URL}{created['id']}/history/").json()["data"]
        # Newest first — the update is index 0, creation is index 1.
        assert len(records) == 2
        update = records[0]
        creation = records[1]

        assert update["history_type"] == "~"
        assert creation["history_type"] == "+"
        assert update["changed_fields"] == {
            "status": {"from": "planning", "to": "active"},
            "description": {"from": "orig", "to": "updated"},
        }

    def test_shell_edit_has_null_history_user(self, owner_client, project_factory):
        """Edits outside an HTTP request have `history_user = None`."""
        client, user, _, alpha = owner_client
        project = project_factory(organization=alpha, actor=user, name="H3")

        # Direct ORM save — no request context.
        project.name = "H3-renamed"
        project.save(update_fields=["name", "modified_at"])

        records = client.get(f"{PROJECTS_URL}{project.public_id}/history/").json()["data"]
        assert len(records) == 2
        shell_record = records[0]
        assert shell_record["history_type"] == "~"
        assert shell_record["history_user"] is None

    def test_history_scoped_to_organization(self, owner_client, project_factory, two_orgs, user_factory):
        client, user, _, _ = owner_client
        _, bravo = two_orgs
        bravo_project = project_factory(organization=bravo, actor=user, name="X")

        response = client.get(f"{PROJECTS_URL}{bravo_project.public_id}/history/")
        # Cross-tenant returns 404 (per ADR 005), not 403.
        assert response.status_code == 404
