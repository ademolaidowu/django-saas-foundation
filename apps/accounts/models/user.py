"""Custom user model — email as identity, no username."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from core.models.base import BaseModel


class UserManager(BaseUserManager["User"]):
    """Email-based user creation. Password is hashed; email is lowercased."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> User:
        if not email:
            raise ValueError("Email must be set.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password is None:
            user.set_unusable_password()
        else:
            user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Email-based user. No username. Carries `BaseModel` (public_id, soft-delete,
    timestamps) but not `AuditTrailMixin` — a self-referential actor FK on the
    first user is awkward and provides no value.
    """

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ("-created_at",)

    email = models.EmailField(verbose_name="email", unique=True)
    first_name = models.CharField(verbose_name="first name", max_length=150, blank=True, default="")
    last_name = models.CharField(verbose_name="last name", max_length=150, blank=True, default="")

    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin.",
    )

    objects = UserManager()  # type: ignore[assignment,misc]

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []  # type: ignore[misc]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p).strip()
