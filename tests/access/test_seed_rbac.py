"""`manage.py seed_rbac` — idempotent, codes match registry.py."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from access.models.permission import Permission
from access.registry import PERMISSIONS


@pytest.mark.django_db
class TestSeedRBAC:
    def test_seeds_every_registry_code(self):
        call_command("seed_rbac", verbosity=0)
        db_codes = set(Permission.objects.values_list("code", flat=True))
        registry_codes = {p.code for p in PERMISSIONS}
        assert db_codes == registry_codes

    def test_module_extracted_from_code(self):
        call_command("seed_rbac", verbosity=0)
        for p in Permission.objects.all():
            assert p.code.startswith(f"{p.module}.")

    def test_idempotent(self):
        call_command("seed_rbac", verbosity=0)
        before = Permission.objects.count()
        call_command("seed_rbac", verbosity=0)
        call_command("seed_rbac", verbosity=0)
        assert Permission.objects.count() == before

    def test_description_updates_on_rerun(self):
        """If registry.py changes a description, seed_rbac rewrites it."""
        call_command("seed_rbac", verbosity=0)
        p = Permission.objects.first()
        original = p.description
        Permission.objects.filter(pk=p.pk).update(description="tampered")
        call_command("seed_rbac", verbosity=0)
        p.refresh_from_db()
        assert p.description == original
