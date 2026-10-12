"""Object-level authorization for accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accounts.constants import AccountStatus

if TYPE_CHECKING:
    from accounts.models.account import Account
    from accounts.models.user import User


class AccountPolicy:
    @staticmethod
    def can_switch_to(user: User, target: Account) -> bool:
        return target.user_id == user.id and target.status == AccountStatus.ACTIVE
