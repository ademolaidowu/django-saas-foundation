"""
Direct tests for `core.models.base` paths not exercised by the view layer:
`hard_delete`, `AuditTrailMixin.delete` validation, `BaseQuerySet.get_or_none`.
"""

from __future__ import annotations

import pytest
from django.db import transaction

from accounts.models.account import Account
from tenants.models.organization import Organization


@pytest.mark.django_db
class TestBaseQuerySet:
    """BaseQuerySet.get_or_none — exposed via BaseManager (Organization uses it directly)."""

    def test_get_or_none_miss_returns_none(self):
        assert Organization.objects.get_or_none(slug="ghost") is None

    def test_get_or_none_hit(self):
        org = Organization.objects.create(name="O", slug="o")
        assert Organization.objects.get_or_none(slug="o") == org


@pytest.mark.django_db
class TestSoftDeleteAndHardDelete:
    def test_soft_delete_marks_deleted_at(self):
        org = Organization.objects.create(name="X", slug="x")
        org.delete()
        org.refresh_from_db()
        assert org.deleted_at is not None
        assert org.is_deleted() is True

    def test_hard_delete_removes_row(self):
        org = Organization.objects.create(name="HD", slug="hd")
        pk = org.pk
        org.hard_delete()
        assert not Organization.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestAuditTrailMixinDelete:
    def test_delete_requires_deleted_by(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = Account.objects.create(
            user=user,
            organization=alpha,
            created_by=user,
            modified_by=user,
        )
        with pytest.raises(ValueError, match="deleted_by"):
            account.delete()  # missing deleted_by

    def test_delete_stamps_deleted_by_and_deleted_at(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        actor = user_factory(email="actor@example.com")
        account = Account.objects.create(
            user=user,
            organization=alpha,
            created_by=user,
            modified_by=user,
        )
        account.delete(deleted_by=actor)
        account.refresh_from_db()
        assert account.deleted_at is not None
        assert account.deleted_by == actor


@pytest.mark.django_db(transaction=True)
class TestSelectForUpdate:
    def test_select_for_update_returns_fresh_locked_instance(self):
        org = Organization.objects.create(name="Y", slug="y")
        with transaction.atomic():
            locked = org.select_for_update()
            assert locked.pk == org.pk
