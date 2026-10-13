"""
Row-level tenancy.

Everything that belongs to an `Organization` extends `TenantScopedModel`. Its
default managers (`objects`, `records`) return a `TenantScopedQuerySet` that
*refuses to evaluate* until `.for_organization(org)` or `.unsafe_all()` has
been called in the chain. This is the headline guard — see ADR 003.

The guard sits at the queryset layer (not the manager), so every evaluation
entry point — `__iter__`, `count`, `exists`, `get`, `first`, `last`, `update`,
`delete` — is protected regardless of how it was reached.

Reverse accessors (`organization.project_set.all()`) auto-scope: Django's
`RelatedManager` sets `self.instance` before calling `get_queryset()`, which
we use as the signal to pre-mark the queryset scoped.
"""

from __future__ import annotations

import warnings
from typing import Any, Self

from django.conf import settings
from django.db import models

from core.exceptions import UnscopedQueryError
from core.models.base import BaseModel, BaseQuerySet

_SCOPED_ATTR = "_tenant_scoped"


class TenantScopedQuerySet(BaseQuerySet):
    """QuerySet that refuses to evaluate without an explicit tenant scope."""

    def _clone(self, **kwargs: Any) -> Self:  # type: ignore[misc]
        clone = super()._clone(**kwargs)  # type: ignore[misc]
        # Preserve scope flag across .filter() / .exclude() / .order_by() / etc.
        setattr(clone, _SCOPED_ATTR, getattr(self, _SCOPED_ATTR, False))
        return clone

    def _chain(self, **kwargs: Any) -> Self:  # type: ignore[misc]
        chained = super()._chain(**kwargs)  # type: ignore[misc]
        setattr(chained, _SCOPED_ATTR, getattr(self, _SCOPED_ATTR, False))
        return chained

    def for_organization(self, organization: Any) -> Self:
        """Scope this queryset to a single organization. The sanctioned entry point."""
        if organization is None:
            raise UnscopedQueryError("for_organization(None) is not allowed.")
        qs = self.filter(organization=organization)
        setattr(qs, _SCOPED_ATTR, True)
        return qs

    def unsafe_all(self) -> Self:
        """
        Explicit escape hatch — bypasses the guard.

        For admin changelists, migrations, data-fix scripts, and the Django
        shell. Logs a `RuntimeWarning` so the opt-out is visible in logs.
        """
        warnings.warn(
            f"unsafe_all() called on {self.model.__name__} — tenant guard bypassed.",
            RuntimeWarning,
            stacklevel=2,
        )
        qs = self._chain()
        setattr(qs, _SCOPED_ATTR, True)
        return qs

    # ------- guard hooks -------
    def _check_scoped(self) -> None:
        if getattr(self, _SCOPED_ATTR, False):
            return
        if not getattr(settings, "TENANT_GUARD_ENABLED", True):
            return
        mode = getattr(settings, "TENANT_GUARD_MODE", "strict")
        msg = f"Unscoped query on {self.model.__name__}. Call .for_organization(org) or .unsafe_all() first."
        if mode == "warn":
            warnings.warn(msg, RuntimeWarning, stacklevel=3)
            return
        raise UnscopedQueryError(msg)

    def _fetch_all(self) -> None:
        self._check_scoped()
        super()._fetch_all()

    def iterator(self, *args: Any, **kwargs: Any) -> Any:
        self._check_scoped()
        return super().iterator(*args, **kwargs)

    def count(self) -> int:
        self._check_scoped()
        return super().count()

    def exists(self) -> bool:
        self._check_scoped()
        return super().exists()

    def get(self, *args: Any, **kwargs: Any) -> Any:
        # `get` ultimately calls `_fetch_all`, but raising here gives a cleaner trace.
        self._check_scoped()
        return super().get(*args, **kwargs)

    def first(self) -> Any:
        self._check_scoped()
        return super().first()

    def last(self) -> Any:
        self._check_scoped()
        return super().last()

    def update(self, **kwargs: Any) -> int:
        self._check_scoped()
        return super().update(**kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:
        self._check_scoped()
        return super().delete()


class TenantManager(models.Manager):
    """
    Returns a `TenantScopedQuerySet` from a tenant model. All rows (including
    soft-deleted); use `TenantRecordsManager` for the alive-only variant.

    When used as a reverse accessor (`organization.project_set`), Django's
    `RelatedManager` sets `self.instance` before calling `get_queryset()`; we
    use that signal to pre-mark the queryset scoped so related lookups work
    without an explicit `.for_organization(...)` call.
    """

    _alive_only: bool = False

    def get_queryset(self) -> TenantScopedQuerySet:
        qs: TenantScopedQuerySet = TenantScopedQuerySet(self.model, using=self._db)
        if self._alive_only:
            qs = qs.alive()
        if getattr(self, "instance", None) is not None:
            setattr(qs, _SCOPED_ATTR, True)
        return qs

    def for_organization(self, organization: Any) -> TenantScopedQuerySet:
        return self.get_queryset().for_organization(organization)

    def unsafe_all(self) -> TenantScopedQuerySet:
        return self.get_queryset().unsafe_all()

    def get_or_none(self, *args: Any, **kwargs: Any) -> Any | None:
        return self.get_queryset().get_or_none(*args, **kwargs)


class TenantRecordsManager(TenantManager):
    """`records` manager for tenant models — alive rows only, still guarded."""

    _alive_only = True


class TenantScopedModel(BaseModel):
    """
    Abstract base for every row owned by an `Organization`.

    Adds the `organization` FK and swaps the base managers for guarded ones.
    Child models should override `related_name` / `related_query_name` on the
    FK via `Meta` or by redeclaring the field with a sensible name, since the
    default `related_name="+"` suppresses reverse accessors.
    """

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["organization", "deleted_at"]),
        ]

    organization = models.ForeignKey(
        "tenants.Organization",
        verbose_name="organization",
        on_delete=models.PROTECT,
        related_name="+",
        related_query_name="+",
        db_index=True,
    )

    objects = TenantManager()  # type: ignore[assignment,misc]
    records = TenantRecordsManager()  # type: ignore[assignment,misc]
