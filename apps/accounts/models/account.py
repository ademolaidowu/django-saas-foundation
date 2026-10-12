"""Account — the User × Organization join and the unit a token is scoped to."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from accounts.constants import AccountStatus
from core.models.base import AuditTrailMixin, BaseModel


class Account(AuditTrailMixin, BaseModel):
    """
    One `Account` per (user, organization) pair. The subject of every
    authenticated request — the Knox token binds to it, and `request.account`
    + `request.organization` are derived from it.

    Deliberately NOT a `TenantScopedModel`: it has an `organization` FK but is
    *queried by user* ("show me my accounts"), not by organization context,
    so the tenant guard would reject the common lookup.
    """

    class Meta:
        db_table = "accounts"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        ordering = ("-is_primary", "joined_at")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_account_per_user_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="user",
        on_delete=models.CASCADE,
        related_name="accounts",
        related_query_name="account",
    )
    organization = models.ForeignKey(
        "tenants.Organization",
        verbose_name="organization",
        on_delete=models.CASCADE,
        related_name="accounts",
        related_query_name="account",
    )
    status = models.CharField(
        verbose_name="status",
        max_length=AccountStatus.max_name_length(),
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    is_primary = models.BooleanField(
        verbose_name="is primary",
        default=False,
        help_text="Default account selected on login.",
    )
    joined_at = models.DateTimeField(verbose_name="joined at", auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization}"
