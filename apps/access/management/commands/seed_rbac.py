"""
Idempotent seed of the `access.Permission` table from `apps/access/registry.py`.

Run on every deploy and after any edit to `registry.py`. System roles are
NOT seeded here — those are per-organization and are created on registration
by `RoleService.create_system_roles_for_organization`.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from access.models.permission import Permission
from access.registry import PERMISSIONS


class Command(BaseCommand):
    help = "Upsert permission rows from access.registry. Idempotent."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        created = 0
        updated = 0
        for p in PERMISSIONS:
            _, was_created = Permission.objects.update_or_create(
                code=p.code,
                defaults={
                    "module": p.code.split(".", 1)[0],
                    "description": p.description,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"seed_rbac: {created} created, {updated} updated, {len(PERMISSIONS)} total.")
        )
