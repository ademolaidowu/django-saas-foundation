"""
Tenant isolation guard tests.

These assert the headline promise of the project: a `TenantScopedQuerySet`
refuses to evaluate unless it has been scoped via `.for_organization(org)`
or explicitly opted out via `.unsafe_all()`. See ADR 003.
"""

from __future__ import annotations

import warnings

import pytest
from django.test import override_settings

from core.exceptions import UnscopedQueryError


@pytest.mark.django_db
class TestTenantGuardStrict:
    """TENANT_GUARD_MODE='strict' (the test-settings default) — guard raises."""

    @pytest.mark.parametrize(
        "evaluator",
        [
            pytest.param(lambda qs: list(qs), id="list"),
            pytest.param(lambda qs: qs.count(), id="count"),
            pytest.param(lambda qs: qs.exists(), id="exists"),
            pytest.param(lambda qs: qs.first(), id="first"),
            pytest.param(lambda qs: qs.last(), id="last"),
            pytest.param(lambda qs: list(qs.iterator()), id="iterator"),
            pytest.param(lambda qs: qs.update(name="x"), id="update"),
            pytest.param(lambda qs: qs.delete(), id="delete"),
        ],
    )
    def test_unscoped_query_raises(self, widget_model, two_orgs, evaluator):
        alpha, _ = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")
        with pytest.raises(UnscopedQueryError):
            evaluator(widget_model.records.all())

    def test_unscoped_get_raises(self, widget_model, two_orgs):
        alpha, _ = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")
        with pytest.raises(UnscopedQueryError):
            widget_model.records.get(name="a1")

    def test_scoped_query_returns_only_its_rows(self, widget_model, two_orgs):
        alpha, bravo = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")
        widget_model.objects.create(organization=alpha, name="a2")
        widget_model.objects.create(organization=bravo, name="b1")

        alpha_names = list(widget_model.records.for_organization(alpha).values_list("name", flat=True))
        bravo_names = list(widget_model.records.for_organization(bravo).values_list("name", flat=True))

        assert sorted(alpha_names) == ["a1", "a2"]
        assert bravo_names == ["b1"]
        assert widget_model.records.for_organization(alpha).count() == 2
        assert widget_model.records.for_organization(bravo).count() == 1

    def test_scoping_survives_chained_filters(self, widget_model, two_orgs):
        alpha, bravo = two_orgs
        widget_model.objects.create(organization=alpha, name="keep")
        widget_model.objects.create(organization=alpha, name="skip")
        widget_model.objects.create(organization=bravo, name="keep")

        qs = widget_model.records.for_organization(alpha).filter(name="keep").order_by("name")
        assert list(qs.values_list("name", flat=True)) == ["keep"]

    def test_for_organization_none_raises(self, widget_model):
        with pytest.raises(UnscopedQueryError):
            widget_model.records.for_organization(None)

    def test_unsafe_all_bypasses_guard(self, widget_model, two_orgs):
        alpha, bravo = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")
        widget_model.objects.create(organization=bravo, name="b1")

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            total = widget_model.records.unsafe_all().count()

        assert total == 2
        assert any("unsafe_all" in str(w.message) for w in recorded)

    def test_objects_manager_is_also_guarded(self, widget_model, two_orgs):
        """`objects` returns all rows including deleted; it is still guarded."""
        alpha, _ = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")
        with pytest.raises(UnscopedQueryError):
            list(widget_model.objects.all())

    def test_objects_scoped_returns_all_rows_including_deleted(self, widget_model, two_orgs):
        alpha, _ = two_orgs
        a1 = widget_model.objects.create(organization=alpha, name="a1")
        a2 = widget_model.objects.create(organization=alpha, name="a2")
        a1.deleted_at = a1.modified_at
        a1.save(update_fields=["deleted_at"])

        assert widget_model.objects.for_organization(alpha).count() == 2
        assert widget_model.records.for_organization(alpha).count() == 1
        assert a2 in widget_model.records.for_organization(alpha)


@pytest.mark.django_db
class TestTenantGuardWarnMode:
    """TENANT_GUARD_MODE='warn' — guard warns instead of raising."""

    @override_settings(TENANT_GUARD_MODE="warn")
    def test_unscoped_query_warns(self, widget_model, two_orgs):
        alpha, _ = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            count = widget_model.records.all().count()

        assert count == 1
        assert any("Unscoped query" in str(w.message) for w in recorded)

    @override_settings(TENANT_GUARD_ENABLED=False)
    def test_guard_fully_disabled_is_silent(self, widget_model, two_orgs):
        alpha, _ = two_orgs
        widget_model.objects.create(organization=alpha, name="a1")

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            count = widget_model.records.all().count()

        assert count == 1
        assert not any("Unscoped query" in str(w.message) for w in recorded)


@pytest.mark.django_db
class TestOrganizationNotGuarded:
    """`Organization` extends `BaseModel`, not `TenantScopedModel` — it IS the tenant."""

    def test_organization_queries_work_without_scope(self, two_orgs):
        from tenants.models.organization import Organization

        assert Organization.objects.count() == 2
        assert Organization.objects.filter(slug="alpha").exists()
