"""
Shared pytest fixtures.

The `widget_model` fixture dynamically builds a `TenantScopedModel` subclass
and its database table so isolation tests can exercise the guard against a
real tenant-scoped model without taking a dependency on any specific domain
app (which don't exist in Phase 1 yet). The table is torn down at session end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.db import connection, models

from core.models.tenancy import TenantScopedModel
from tenants.models.organization import Organization

if TYPE_CHECKING:
    pass


@pytest.fixture
def two_orgs(db) -> tuple[Organization, Organization]:
    """Two active organizations named Alpha and Bravo."""
    alpha = Organization.objects.create(name="Alpha", slug="alpha")
    bravo = Organization.objects.create(name="Bravo", slug="bravo")
    return alpha, bravo


@pytest.fixture(scope="session")
def widget_model(django_db_setup, django_db_blocker):
    """
    A throwaway `TenantScopedModel` subclass used by the isolation tests.

    Declared inside the fixture so Django's app registry is already populated
    with the `tenants` app (whose `Organization` the FK targets). The matching
    table is created via `schema_editor` at session start and dropped at end.
    """

    class Widget(TenantScopedModel):
        name = models.CharField(max_length=50)

        class Meta:
            app_label = "tenants"
            db_table = "test_widgets"

        def __str__(self) -> str:
            return self.name

    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.create_model(Widget)

    yield Widget

    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.delete_model(Widget)
