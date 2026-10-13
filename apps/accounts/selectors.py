"""Read-only lookups for the accounts app."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db.models import QuerySet

from accounts.constants import AccountStatus
from accounts.models.account import Account
from accounts.models.user import User

if TYPE_CHECKING:
    from tenants.models.organization import Organization


class UserSelectors:
    @staticmethod
    def get_by_email(email: str) -> User | None:
        return User.objects.filter(email__iexact=email.strip()).first()

    @staticmethod
    def email_exists(email: str) -> bool:
        return User.objects.filter(email__iexact=email.strip()).exists()


class AccountSelectors:
    @staticmethod
    def list_for_user(
        user: User,
        status: str | None = AccountStatus.ACTIVE,
    ) -> QuerySet[Account]:
        qs = Account.records.filter(user=user)
        if status is not None:
            qs = qs.filter(status=status)
        return qs.select_related("organization").order_by("-is_primary", "joined_at")

    @staticmethod
    def get_by_user_and_public_id(
        user: User,
        public_id: uuid.UUID,
    ) -> Account | None:
        return Account.records.filter(user=user, public_id=public_id).select_related("organization").first()

    @staticmethod
    def get_primary_or_first_active(user: User) -> Account | None:
        return (
            Account.records.filter(user=user, status=AccountStatus.ACTIVE)
            .select_related("organization")
            .order_by("-is_primary", "joined_at")
            .first()
        )

    @staticmethod
    def get_by_user_and_organization(user: User, organization: Organization) -> Account | None:
        """The actor's Account on a specific org — used by object-level policies."""
        return Account.records.filter(
            user=user,
            organization=organization,
            status=AccountStatus.ACTIVE,
        ).first()
