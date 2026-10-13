"""
HEADLINE Phase 5 test.

A token binds to one `Account`, and an Account binds to one `Organization`.
Even if the same user holds accounts in multiple orgs, the token issued for
Account A on Org Alpha physically cannot act on Org Bravo. Switching orgs is
a token-issuance operation, not a header flip.

Scenario:
1. Register Alice → Owner on Alpha.
2. Give Alice a second Account on Bravo (as if she accepted a future invite).
3. Alice's Alpha token sees her Bravo account via `/organizations/`, but
   cannot touch any Bravo-scoped endpoint.
4. Alice calls `/switch-organization/` → new token for Bravo, old cookie
   dropped from the server.
5. The old cookie, if replayed by an attacker, fails 401.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from access.constants import SystemRoleCode
from access.services import RoleAssignmentService, RoleService
from accounts.constants import AccountStatus
from accounts.models.account import Account
from projects.constants import ProjectStatus
from projects.models.project import Project

REGISTER_URL = "/api/auth/register/"
SWITCH_URL = "/api/auth/switch-organization/"
ORGS_URL = "/api/auth/organizations/"


@pytest.mark.django_db
class TestCrossOrgTokenCannotLeak:
    def test_alpha_token_cannot_reach_bravo_resources(self, api_client, two_orgs, user_factory, password):
        alpha, bravo = two_orgs

        # Register Alice → Alpha with Owner role seeded automatically
        resp = api_client.post(
            REGISTER_URL,
            {
                "email": "alice@acme.com",
                "password": password,
                "first_name": "Alice",
                "last_name": "A",
                "organization_name": alpha.name,
                "organization_slug": "alpha-registered",
            },
            format="json",
        )
        assert resp.status_code == 201
        alice = (
            user_factory.__wrapped__ if hasattr(user_factory, "__wrapped__") else None
        )  # placeholder; replaced below
        from accounts.models.user import User as _User

        alice = _User.objects.get(email="alice@acme.com")
        alpha = Account.records.get(user=alice).organization

        # Simulate Alice accepting a future Bravo invite via direct ORM
        alice_bravo = Account.objects.create(
            user=alice,
            organization=bravo,
            status=AccountStatus.ACTIVE,
            is_primary=False,
            created_by=alice,
            modified_by=alice,
        )
        bravo_roles = RoleService.create_system_roles_for_organization(organization=bravo, created_by=alice)
        RoleAssignmentService.assign(
            account=alice_bravo,
            role=bravo_roles[SystemRoleCode.OWNER],
            assigned_by=alice,
        )
        bravo_project = Project.objects.create(
            organization=bravo,
            name="Bravo",
            description="",
            status=ProjectStatus.ACTIVE,
            created_by=alice,
            modified_by=alice,
        )

        # Alice can see both of her accounts
        orgs_resp = api_client.get(ORGS_URL)
        assert orgs_resp.status_code == 200
        org_slugs = {a["organization"]["slug"] for a in orgs_resp.json()["data"]}
        assert org_slugs == {"alpha-registered", bravo.slug}

        # The Alpha token cannot resolve the Bravo project UUID
        detail_resp = api_client.get(f"/api/projects/{bravo_project.public_id}/")
        assert detail_resp.status_code == 404

    def test_switch_rotates_token_and_old_token_dies(
        self, api_client, two_orgs, user_factory, account_factory, password
    ):
        alpha, bravo = two_orgs
        alice = user_factory(email="alice@acme.com")
        alice_alpha = account_factory(user=alice, organization=alpha, is_primary=True)
        alice_bravo = account_factory(user=alice, organization=bravo, is_primary=False)

        alpha_roles = RoleService.create_system_roles_for_organization(organization=alpha, created_by=alice)
        bravo_roles = RoleService.create_system_roles_for_organization(organization=bravo, created_by=alice)
        RoleAssignmentService.assign(
            account=alice_alpha,
            role=alpha_roles[SystemRoleCode.OWNER],
            assigned_by=alice,
        )
        RoleAssignmentService.assign(
            account=alice_bravo,
            role=bravo_roles[SystemRoleCode.OWNER],
            assigned_by=alice,
        )
        bravo_project = Project.objects.create(
            organization=bravo,
            name="Bravo",
            description="",
            status=ProjectStatus.ACTIVE,
            created_by=alice,
            modified_by=alice,
        )

        # Login as Alice → bound to Alpha (primary)
        login = api_client.post(
            "/api/auth/login/",
            {"email": alice.email, "password": password},
            format="json",
        )
        assert login.status_code == 200
        old_cookie = api_client.cookies[settings.AUTH_COOKIE_NAME].value

        # Cross-org attempt — fails
        assert api_client.get(f"/api/projects/{bravo_project.public_id}/").status_code == 404

        # Switch to the Bravo account
        switch = api_client.post(SWITCH_URL, {"account_id": str(alice_bravo.public_id)}, format="json")
        assert switch.status_code == 200
        new_cookie = api_client.cookies[settings.AUTH_COOKIE_NAME].value
        assert new_cookie != old_cookie

        # Now the same project is visible
        assert api_client.get(f"/api/projects/{bravo_project.public_id}/").status_code == 200

        # Replay the old cookie from a stale attacker
        attacker = APIClient()
        attacker.cookies[settings.AUTH_COOKIE_NAME] = old_cookie
        stale = attacker.get("/api/auth/me/")
        assert stale.status_code == 401
