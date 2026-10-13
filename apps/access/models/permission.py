"""Global `Permission` registry — one row per code, shared across all organizations."""

from __future__ import annotations

from django.db import models

from core.models.base import BaseModel


class Permission(BaseModel):
    """
    Reference data. Rows are managed exclusively by the `seed_rbac` management
    command; the admin registers this model read-only.
    """

    class Meta:
        db_table = "permissions"
        ordering = ("module", "code")

    code = models.CharField(max_length=100, unique=True, db_index=True)
    module = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        return self.code
