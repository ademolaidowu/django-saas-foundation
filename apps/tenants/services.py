"""Write operations on tenant-level resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tenants.models.organization import Organization

if TYPE_CHECKING:
    pass


class OrganizationService:
    @staticmethod
    def create_organization(
        *,
        name: str,
        slug: str,
        is_active: bool = True,
    ) -> Organization:
        """Create an organization. Uniqueness-on-slug is enforced at the DB level."""
        return Organization.objects.create(name=name, slug=slug, is_active=is_active)

    @staticmethod
    def slug_exists(slug: str) -> bool:
        return Organization.objects.filter(slug=slug).exists()
