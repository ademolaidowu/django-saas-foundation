"""CRUD on /api/access/roles/."""

from __future__ import annotations

import pytest

from access.models.role import Role

ROLES_URL = "/api/access/roles/"


@pytest.fixture
def owner_client(authed_client, system_roles_for, grant, two_orgs):
    """Phase 2's authed_client holds a bare Account on Alpha. Seed roles + grant Owner."""
    client, user, account = authed_client
    alpha, _ = two_orgs
    system_roles_for(alpha, user)
    grant(account=account, organization=alpha, role_code="owner", assigned_by=user)
    return client, user, account, alpha


@pytest.mark.django_db
class TestRoleCrud:
    def test_list_returns_four_system_roles(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        system_roles_for(alpha, user)  # idempotent

        response = client.get(ROLES_URL)
        assert response.status_code == 200
        codes = sorted(r["code"] for r in response.json()["data"])
        assert codes == ["admin", "member", "owner", "viewer"]

    def test_create_custom_role(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        system_roles_for(alpha, user)

        response = client.post(
            ROLES_URL,
            {
                "name": "Project Lead",
                "description": "Can CRUD projects.",
                "permission_codes": ["projects.read", "projects.create", "projects.update"],
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        body = response.json()["data"]
        assert body["name"] == "Project Lead"
        assert body["is_system"] is False
        assert set(body["permission_codes"]) == {"projects.read", "projects.create", "projects.update"}

    def test_duplicate_name_rejected(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        system_roles_for(alpha, user)
        client.post(ROLES_URL, {"name": "Reviewer", "permission_codes": []}, format="json")

        response = client.post(ROLES_URL, {"name": "Reviewer", "permission_codes": []}, format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "role_0002"

    def test_update_system_role_rejected(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        roles = system_roles_for(alpha, user)
        owner_role = roles["owner"]

        response = client.patch(
            f"{ROLES_URL}{owner_role.public_id}/",
            {"name": "Renamed Owner"},
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "role_0003"

    def test_delete_system_role_rejected(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        roles = system_roles_for(alpha, user)

        response = client.delete(f"{ROLES_URL}{roles['viewer'].public_id}/")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "role_0003"

    def test_delete_custom_role_works(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        system_roles_for(alpha, user)
        created = client.post(ROLES_URL, {"name": "Deletable", "permission_codes": []}, format="json").json()["data"]

        response = client.delete(f"{ROLES_URL}{created['id']}/")
        assert response.status_code == 204

        assert not Role.records.for_organization(alpha).filter(name="Deletable").exists()

    def test_unknown_permission_code_rejected(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        system_roles_for(alpha, user)

        response = client.post(
            ROLES_URL,
            {"name": "Bad Role", "permission_codes": ["does.not.exist"]},
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "role_0004"

    def test_update_replaces_permissions(self, owner_client, system_roles_for):
        client, user, account, alpha = owner_client
        system_roles_for(alpha, user)
        created = client.post(
            ROLES_URL,
            {"name": "Flexible", "permission_codes": ["projects.read"]},
            format="json",
        ).json()["data"]

        response = client.patch(
            f"{ROLES_URL}{created['id']}/",
            {"permission_codes": ["tasks.read", "tasks.create"]},
            format="json",
        )
        assert response.status_code == 200
        assert sorted(response.json()["data"]["permission_codes"]) == ["tasks.create", "tasks.read"]
