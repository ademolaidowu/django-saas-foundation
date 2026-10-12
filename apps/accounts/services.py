"""Write operations and business rules for authentication / accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from accounts.constants import AccountStatus
from accounts.exceptions import LoginError, RegistrationError
from accounts.models.account import Account
from accounts.models.user import User
from accounts.selectors import UserSelectors
from core.exceptions import APIServiceError
from tenants.services import OrganizationService

if TYPE_CHECKING:
    from tenants.models.organization import Organization


class UserService:
    @staticmethod
    def create_user(
        *,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        if UserSelectors.email_exists(email):
            raise APIServiceError(error_code=RegistrationError.EmailTaken)
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )


class AccountService:
    @staticmethod
    def create_account(
        *,
        user: User,
        organization: Organization,
        created_by: User,
        status: str = AccountStatus.ACTIVE,
        is_primary: bool = False,
    ) -> Account:
        return Account.objects.create(
            user=user,
            organization=organization,
            status=status,
            is_primary=is_primary,
            created_by=created_by,
            modified_by=created_by,
        )


class RegistrationService:
    @staticmethod
    @transaction.atomic
    def register(
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_name: str,
        organization_slug: str,
    ) -> tuple[User, Account]:
        """
        Create a user, their organization, and the owner account in one atomic
        transaction. The caller issues the token after this returns.
        """
        if OrganizationService.slug_exists(organization_slug):
            raise APIServiceError(error_code=RegistrationError.SlugTaken)

        user = UserService.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        organization = OrganizationService.create_organization(
            name=organization_name,
            slug=organization_slug,
        )
        account = AccountService.create_account(
            user=user,
            organization=organization,
            created_by=user,
            is_primary=True,
        )
        return user, account


class AuthService:
    @staticmethod
    def authenticate(email: str, password: str) -> User:
        """Validate credentials. Does NOT issue a token (that's the view's job)."""
        user = UserSelectors.get_by_email(email)
        if user is None or not user.check_password(password):
            raise APIServiceError(error_code=LoginError.InvalidCredentials)
        if not user.is_active:
            raise APIServiceError(error_code=LoginError.InactiveUser)
        return user
