"""
Foundation models used by every app in the project.

Two abstract models live here:

- `BaseModel`: fields and behavior shared by every row (public UUID, source,
  timestamps, soft-delete, dual managers).
- `AuditTrailMixin`: user FKs recording the actor who created, modified, or
  soft-deleted the row. Kept separate so system-written rows (tokens,
  notifications, audit records themselves) don't have to carry empty FKs.

Compose with multiple inheritance where a human touches the row:

    class Project(AuditTrailMixin, BaseModel):
        ...

Actor is passed explicitly to services (no middleware, no thread-local, no
signals). See docs/decisions/004 for why `public_id` is UUIDv7.
"""

from __future__ import annotations

import uuid
from typing import Any, Self

import uuid_utils
from django.conf import settings
from django.db import models
from django.utils import timezone


def uuid7() -> uuid.UUID:
    """Return a UUIDv7 as a stdlib `uuid.UUID` (what `UUIDField` validates against)."""
    return uuid.UUID(str(uuid_utils.uuid7()))


class BaseQuerySet(models.QuerySet):
    def get_or_none(self, *args: Any, **kwargs: Any) -> Any | None:
        try:
            return self.get(*args, **kwargs)
        except self.model.DoesNotExist:  # type: ignore[attr-defined]
            return None

    def alive(self) -> Self:
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> Self:
        return self.filter(deleted_at__isnull=False)


class BaseManager(models.Manager):
    """Default manager — returns every row, including soft-deleted."""

    def get_queryset(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db)

    def get_or_none(self, *args: Any, **kwargs: Any) -> Any | None:
        return self.get_queryset().get_or_none(*args, **kwargs)


class RecordsManager(models.Manager):
    """`records` manager — returns alive rows only (`deleted_at IS NULL`)."""

    def get_queryset(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db).alive()

    def get_or_none(self, *args: Any, **kwargs: Any) -> Any | None:
        return self.get_queryset().get_or_none(*args, **kwargs)


class BaseTextChoices(models.TextChoices):
    """`TextChoices` with helpers so field definitions don't repeat themselves."""

    @classmethod
    def max_name_length(cls) -> int:
        return max(len(value) for value, _ in cls.choices)

    @classmethod
    def as_choices(cls) -> list[tuple[str, str]]:
        return cls.choices


class BaseModel(models.Model):
    class Meta:
        abstract = True

    class RecordSource(BaseTextChoices):
        API = "api", "API"
        ADMIN = "admin", "Admin Panel"
        IMPORT = "import", "Bulk Import"
        SYSTEM = "system", "System"
        INTEGRATION = "integration", "Third-Party Integration"
        MIGRATION = "migration", "Data Migration"
        SEED = "seed", "Data Seed / Generation"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        unique=True,
        db_index=True,
        editable=False,
        default=uuid7,
    )
    source = models.CharField(
        max_length=RecordSource.max_name_length(),
        choices=RecordSource.choices,
        default=RecordSource.API,
    )

    created_at = models.DateTimeField(verbose_name="created at", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="modified at", auto_now=True)
    deleted_at = models.DateTimeField(verbose_name="deleted at", blank=True, null=True)

    objects = BaseManager()
    records = RecordsManager()

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def delete(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Soft-delete. `AuditTrailMixin` wraps this to require `deleted_by`."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, *args: Any, **kwargs: Any) -> None:
        """Permanently remove the row. Prefer `delete()` unless you have to."""
        super().delete(*args, **kwargs)

    def select_for_update(self, nowait: bool = False, skip_locked: bool = False) -> Self:
        """Return a fresh row-locked instance of self (must be inside `transaction.atomic`)."""
        return self.__class__.objects.select_for_update(nowait=nowait, skip_locked=skip_locked).get(pk=self.pk)


class AuditTrailMixin(models.Model):
    """
    Adds `created_by` / `modified_by` / `deleted_by` user FKs.

    Compose with `BaseModel` on any row a human touches through the API:

        class Project(AuditTrailMixin, BaseModel):
            ...

    Skip on rows that the system writes automatically (tokens, audit logs,
    notifications) and on system reference data (Permission, Role templates).

    The acting user is passed explicitly to service methods — the write
    layer sets these fields. No middleware, no thread-locals, no signals.
    `related_name="+"` because reverse accessors from User to every audited
    row would be unused clutter.
    """

    class Meta:
        abstract = True

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="created by",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name="+",
        related_query_name="+",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="modified by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        related_query_name="+",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="deleted by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        related_query_name="+",
    )

    def delete(self, deleted_by: Any = None, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        if deleted_by is None:
            raise ValueError("deleted_by is required for soft delete")
        self.deleted_by = deleted_by
        super().delete(*args, **kwargs)
