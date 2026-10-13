"""Smoke tests for the `seed_demo` management command."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from accounts.models.account import Account
from accounts.models.user import User
from projects.models.project import Project
from projects.models.task import Task
from tenants.models.organization import Organization

DEMO_PASSWORD = "demopass123"


@pytest.mark.django_db
class TestSeedDemo:
    def test_first_run_creates_fixed_dataset(self):
        call_command("seed_demo", verbosity=0)

        assert Organization.objects.count() == 2
        assert set(Organization.objects.values_list("slug", flat=True)) == {"acme", "globex"}
        assert User.objects.count() == 4
        assert set(User.objects.values_list("email", flat=True)) == {
            "alice@acme.com",
            "bob@acme.com",
            "carol@acme.com",
            "dave@both.com",
        }
        assert Account.objects.count() == 5  # dave appears in both orgs
        assert Project.objects.unsafe_all().count() == 4
        assert Task.objects.unsafe_all().count() == 6

    def test_idempotent_on_rerun(self):
        call_command("seed_demo", verbosity=0)
        before = (
            Organization.objects.count(),
            User.objects.count(),
            Account.objects.count(),
            Project.objects.unsafe_all().count(),
            Task.objects.unsafe_all().count(),
        )
        call_command("seed_demo", verbosity=0)
        after = (
            Organization.objects.count(),
            User.objects.count(),
            Account.objects.count(),
            Project.objects.unsafe_all().count(),
            Task.objects.unsafe_all().count(),
        )
        assert before == after

    def test_demo_user_can_login(self, api_client):
        call_command("seed_demo", verbosity=0)
        response = api_client.post(
            "/api/auth/login/",
            {"email": "alice@acme.com", "password": DEMO_PASSWORD},
            format="json",
        )
        assert response.status_code == 200

    def test_dave_has_accounts_in_both_orgs(self):
        call_command("seed_demo", verbosity=0)
        dave = User.objects.get(email="dave@both.com")
        slugs = set(dave.accounts.values_list("organization__slug", flat=True))
        assert slugs == {"acme", "globex"}
