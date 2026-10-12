"""Binds a Knox `AuthToken` to a specific `Account`. The isolation guarantee."""

from __future__ import annotations

from django.db import models
from knox.models import AuthToken


class AccountToken(models.Model):
    """
    One row per issued Knox token, hard-linking it to the Account the token
    was issued for. The custom authentication class loads this chain
    (AuthToken → AccountToken → Account → Organization) on every request to
    derive `request.account` and `request.organization`.

    Deliberately not a `BaseModel` subclass: this is a bare system row with no
    human lifecycle. No `public_id`, no soft-delete, no audit FKs — Knox's
    `AuthToken.user` already records who the token belongs to.
    """

    class Meta:
        db_table = "account_tokens"
        indexes = [
            models.Index(fields=["account"]),
        ]

    auth_token = models.OneToOneField(
        AuthToken,
        on_delete=models.CASCADE,
        related_name="account_context",
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    def __str__(self) -> str:
        return f"AccountToken({self.account_id})"
