"""
Idempotent demo data: two organizations, four users (one in both),
projects, and tasks. Running twice yields the same count.

Usage:
    uv run python manage.py seed_rbac       # if not already seeded
    uv run python manage.py seed_demo

Login (password: `demopass123`):
  - alice@acme.com    (Owner  on Acme)
  - bob@acme.com      (Member on Acme)
  - carol@acme.com    (Viewer on Acme)
  - dave@both.com     (Owner  on Globex, Member on Acme)
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from access.constants import SystemRoleCode
from access.services import RoleAssignmentService, RoleService
from accounts.constants import AccountStatus
from accounts.models.account import Account
from accounts.models.user import User
from projects.constants import ProjectStatus, TaskStatus
from projects.models.project import Project
from projects.models.task import Task
from tenants.models.organization import Organization

PASSWORD = "demopass123"


def _upsert_user(email: str, first: str, last: str) -> User:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": first,
            "last_name": last,
            "password": make_password(PASSWORD),
            "is_active": True,
            "is_email_verified": True,
        },
    )
    if not created and not user.has_usable_password():
        user.password = make_password(PASSWORD)
        user.save(update_fields=["password"])
    return user


def _upsert_org(name: str, slug: str) -> Organization:
    org, _ = Organization.objects.get_or_create(
        slug=slug,
        defaults={"name": name, "is_active": True},
    )
    return org


def _upsert_account(user: User, organization: Organization, is_primary: bool) -> Account:
    account, _ = Account.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={
            "status": AccountStatus.ACTIVE,
            "is_primary": is_primary,
            "created_by": user,
            "modified_by": user,
        },
    )
    return account


def _upsert_project(
    organization: Organization,
    name: str,
    description: str,
    status: str,
    created_by: User,
) -> Project:
    existing = Project.records.for_organization(organization).filter(name=name).first()
    if existing is not None:
        return existing
    return Project.objects.create(
        organization=organization,
        name=name,
        description=description,
        status=status,
        created_by=created_by,
        modified_by=created_by,
    )


def _upsert_task(
    project: Project,
    title: str,
    status: str,
    assignee: Account | None,
    due_offset_days: int | None,
    created_by: User,
) -> Task:
    existing = Task.records.for_organization(project.organization).filter(project=project, title=title).first()
    if existing is not None:
        return existing
    return Task.objects.create(
        organization=project.organization,
        project=project,
        title=title,
        description="",
        status=status,
        assignee=assignee,
        due_date=(_dt.date(2026, 1, 1) + _dt.timedelta(days=due_offset_days) if due_offset_days is not None else None),
        created_by=created_by,
        modified_by=created_by,
    )


class Command(BaseCommand):
    help = "Seed a fixed, reproducible demo dataset."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        # Users
        alice = _upsert_user("alice@acme.com", "Alice", "Anderson")
        bob = _upsert_user("bob@acme.com", "Bob", "Brown")
        carol = _upsert_user("carol@acme.com", "Carol", "Clark")
        dave = _upsert_user("dave@both.com", "Dave", "Doyle")

        # Orgs
        acme = _upsert_org("Acme Corporation", "acme")
        globex = _upsert_org("Globex Innovations", "globex")

        # System roles per org — idempotent (keyed on org + role code)
        acme_roles = RoleService.create_system_roles_for_organization(organization=acme, created_by=alice)
        globex_roles = RoleService.create_system_roles_for_organization(organization=globex, created_by=dave)

        # Accounts
        alice_acme = _upsert_account(alice, acme, is_primary=True)
        bob_acme = _upsert_account(bob, acme, is_primary=True)
        carol_acme = _upsert_account(carol, acme, is_primary=True)
        dave_acme = _upsert_account(dave, acme, is_primary=False)
        dave_globex = _upsert_account(dave, globex, is_primary=True)

        # Role assignments
        RoleAssignmentService.assign(account=alice_acme, role=acme_roles[SystemRoleCode.OWNER], assigned_by=alice)
        RoleAssignmentService.assign(account=bob_acme, role=acme_roles[SystemRoleCode.MEMBER], assigned_by=alice)
        RoleAssignmentService.assign(account=carol_acme, role=acme_roles[SystemRoleCode.VIEWER], assigned_by=alice)
        RoleAssignmentService.assign(account=dave_acme, role=acme_roles[SystemRoleCode.MEMBER], assigned_by=alice)
        RoleAssignmentService.assign(account=dave_globex, role=globex_roles[SystemRoleCode.OWNER], assigned_by=dave)

        # Projects
        acme_mvp = _upsert_project(
            acme,
            "Launch MVP",
            "Ship the first customer-facing release.",
            ProjectStatus.ACTIVE,
            alice,
        )
        acme_rewrite = _upsert_project(
            acme,
            "Platform Rewrite",
            "Migrate the legacy monolith.",
            ProjectStatus.PLANNING,
            alice,
        )
        globex_rocket = _upsert_project(
            globex,
            "Rocket Delivery",
            "Build the rocket-powered delivery drone.",
            ProjectStatus.ACTIVE,
            dave,
        )
        _upsert_project(
            globex,
            "Feasibility Study",
            "Validate rocket thrust safety envelope.",
            ProjectStatus.ON_HOLD,
            dave,
        )

        # Tasks
        _upsert_task(acme_mvp, "Draft architecture doc", TaskStatus.DONE, alice_acme, 7, alice)
        _upsert_task(acme_mvp, "Build auth flow", TaskStatus.IN_PROGRESS, bob_acme, 14, alice)
        _upsert_task(acme_mvp, "Set up analytics", TaskStatus.TODO, bob_acme, 21, alice)
        _upsert_task(acme_rewrite, "Scope legacy inventory", TaskStatus.IN_PROGRESS, alice_acme, 30, alice)
        _upsert_task(globex_rocket, "Design hull", TaskStatus.TODO, dave_globex, 10, dave)
        _upsert_task(globex_rocket, "Order engines", TaskStatus.TODO, dave_globex, 20, dave)

        counts = {
            "organizations": Organization.objects.count(),
            "users": User.objects.count(),
            "accounts": Account.objects.count(),
            "projects": Project.objects.unsafe_all().count(),
            "tasks": Task.objects.unsafe_all().count(),
        }
        self.stdout.write(self.style.SUCCESS("seed_demo complete:"))
        for label, n in counts.items():
            self.stdout.write(f"  {label}: {n}")
        self.stdout.write(f"  password: {PASSWORD}")
