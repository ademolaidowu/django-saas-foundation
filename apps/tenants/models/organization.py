"""The tenant itself. Extends `BaseModel`, NOT `TenantScopedModel`."""

from __future__ import annotations

from django.db import models

from core.models.base import BaseModel


class Organization(BaseModel):
    class Meta:
        db_table = "organizations"
        ordering = ("name",)

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
