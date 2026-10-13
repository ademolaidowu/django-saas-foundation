"""
HEADLINE Phase 4 test: only the assignee or an Owner/Admin can close a task.
"Close" = transition status to `done` or `cancelled`.
"""

from __future__ import annotations

import pytest

from access.constants import SystemRoleCode

TASKS_URL = "/api/tasks/"


@pytest.fixture
def task_setup(
    api_client,
    user_factory,
    account_factory,
    seed_system_roles,
    grant_role,
    project_factory,
    task_factory,
    two_orgs,
    password,
):
    """
    Alpha org with four accounts: Alice (Owner), Bob (Member assignee),
    Carol (Member non-assignee), Dan (Admin non-assignee).
    One project with one task assigned to Bob.
    """
    alpha, _ = two_orgs

    alice = user_factory(email="alice@acme.com")
    bob = user_factory(email="bob@acme.com")
    carol = user_factory(email="carol@acme.com")
    dan = user_factory(email="dan@acme.com")

    alice_acc = account_factory(user=alice, organization=alpha, is_primary=True)
    bob_acc = account_factory(user=bob, organization=alpha, is_primary=True)
    carol_acc = account_factory(user=carol, organization=alpha, is_primary=True)
    dan_acc = account_factory(user=dan, organization=alpha, is_primary=True)

    seed_system_roles(alpha, alice)
    grant_role(account=alice_acc, role_code=SystemRoleCode.OWNER, assigned_by=alice)
    grant_role(account=bob_acc, role_code=SystemRoleCode.MEMBER, assigned_by=alice)
    grant_role(account=carol_acc, role_code=SystemRoleCode.MEMBER, assigned_by=alice)
    grant_role(account=dan_acc, role_code=SystemRoleCode.ADMIN, assigned_by=alice)

    project = project_factory(organization=alpha, actor=alice)
    task = task_factory(project=project, actor=alice, assignee=bob_acc, title="Close me")

    def _login(email):
        from rest_framework.test import APIClient

        c = APIClient()
        r = c.post("/api/auth/login/", {"email": email, "password": password}, format="json")
        assert r.status_code == 200
        return c

    return {
        "alice": _login(alice.email),
        "bob": _login(bob.email),
        "carol": _login(carol.email),
        "dan": _login(dan.email),
        "task": task,
    }


@pytest.mark.django_db
class TestTaskClosePolicy:
    def test_assignee_can_close_as_done(self, task_setup):
        task = task_setup["task"]
        r = task_setup["bob"].patch(f"{TASKS_URL}{task.public_id}/", {"status": "done"}, format="json")
        assert r.status_code == 200, r.content
        assert r.json()["data"]["status"] == "done"

    def test_assignee_can_close_as_cancelled(self, task_setup):
        task = task_setup["task"]
        r = task_setup["bob"].patch(f"{TASKS_URL}{task.public_id}/", {"status": "cancelled"}, format="json")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "cancelled"

    def test_non_assignee_member_cannot_close(self, task_setup):
        task = task_setup["task"]
        r = task_setup["carol"].patch(f"{TASKS_URL}{task.public_id}/", {"status": "done"}, format="json")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "task_0004"

    def test_admin_non_assignee_can_close(self, task_setup):
        task = task_setup["task"]
        r = task_setup["dan"].patch(f"{TASKS_URL}{task.public_id}/", {"status": "done"}, format="json")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "done"

    def test_owner_non_assignee_can_close(self, task_setup):
        task = task_setup["task"]
        r = task_setup["alice"].patch(f"{TASKS_URL}{task.public_id}/", {"status": "cancelled"}, format="json")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "cancelled"

    def test_non_terminal_update_by_non_assignee_member_succeeds(self, task_setup):
        """The policy only fires on transitions INTO done/cancelled."""
        task = task_setup["task"]
        r = task_setup["carol"].patch(
            f"{TASKS_URL}{task.public_id}/",
            {"title": "Carol retitled this", "status": "in_progress"},
            format="json",
        )
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "Carol retitled this"
