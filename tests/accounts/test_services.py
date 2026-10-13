"""Direct unit tests for accounts services + the UserManager."""

from __future__ import annotations

import pytest

from accounts.exceptions import LoginError, RegistrationError
from accounts.models.user import User
from accounts.services import AccountService, AuthService, RegistrationService, UserService
from core.exceptions import APIServiceError


@pytest.mark.django_db
class TestUserManager:
    def test_create_user_lowercases_email(self):
        user = User.objects.create_user(email="MIX@EXample.com", password="x" * 10)
        assert user.email == "mix@example.com"

    def test_create_user_without_password_marks_unusable(self):
        user = User.objects.create_user(email="pw@example.com", password=None)
        assert not user.has_usable_password()

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser_requires_staff(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="su@example.com", password="x", is_staff=False)

    def test_create_superuser_requires_is_superuser(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="su@example.com", password="x", is_superuser=False)

    def test_create_superuser_happy_path(self):
        su = User.objects.create_superuser(email="su@example.com", password="x" * 10)
        assert su.is_staff and su.is_superuser and su.is_email_verified


@pytest.mark.django_db
class TestUserService:
    def test_create_user_rejects_duplicate_email(self, user_factory):
        user_factory(email="dup@example.com")
        with pytest.raises(APIServiceError) as exc:
            UserService.create_user(email="DUP@example.com", password="testpass123", first_name="", last_name="")
        assert exc.value.error_code is RegistrationError.EmailTaken


@pytest.mark.django_db
class TestAuthService:
    def test_authenticate_wrong_password(self, user_factory):
        user_factory(email="a@example.com", password="correctpass123")
        with pytest.raises(APIServiceError) as exc:
            AuthService.authenticate(email="a@example.com", password="wrong")
        assert exc.value.error_code is LoginError.InvalidCredentials

    def test_authenticate_unknown_email(self):
        with pytest.raises(APIServiceError) as exc:
            AuthService.authenticate(email="ghost@example.com", password="x")
        assert exc.value.error_code is LoginError.InvalidCredentials

    def test_authenticate_inactive_user(self, user_factory):
        user = user_factory(email="inactive@example.com", password="pass12345")
        user.is_active = False
        user.save(update_fields=["is_active"])
        with pytest.raises(APIServiceError) as exc:
            AuthService.authenticate(email=user.email, password="pass12345")
        assert exc.value.error_code is LoginError.InactiveUser

    def test_authenticate_happy_path(self, user_factory):
        user = user_factory(email="b@example.com", password="goodpass123")
        result = AuthService.authenticate(email="b@example.com", password="goodpass123")
        assert result == user


@pytest.mark.django_db
class TestRegistrationService:
    def test_duplicate_slug_rejected(self, two_orgs):
        with pytest.raises(APIServiceError) as exc:
            RegistrationService.register(
                email="new@example.com",
                password="pass12345",
                first_name="",
                last_name="",
                organization_name="Alpha",
                organization_slug="alpha",
            )
        assert exc.value.error_code is RegistrationError.SlugTaken

    def test_atomicity_no_orphan_user_on_role_seed_failure(self, two_orgs, monkeypatch):
        """
        If an exception fires after User + Org + Account are created, the
        whole transaction must roll back — no orphan user. We force the
        failure in `RoleService.create_system_roles_for_organization`.
        """
        from access import services as access_services

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            access_services.RoleService,
            "create_system_roles_for_organization",
            _boom,
        )

        with pytest.raises(RuntimeError):
            RegistrationService.register(
                email="orphan@example.com",
                password="pass12345",
                first_name="",
                last_name="",
                organization_name="New Org",
                organization_slug="new-org",
            )
        assert not User.objects.filter(email="orphan@example.com").exists()


@pytest.mark.django_db
class TestAccountService:
    def test_create_account(self, user_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = AccountService.create_account(user=user, organization=alpha, created_by=user, is_primary=True)
        assert account.user == user
        assert account.organization == alpha
        assert account.is_primary is True
