"""
Internal helper: look up an Account by public_id *within* an organization.

Lives here (not in `apps/accounts/selectors.py`) because the "scope by org"
lookup is specific to access-control flows — the accounts app itself scopes
by user, which is a different thing. Keeping it in access/ avoids pushing
org-scoped Account lookups into the accounts selectors layer.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accounts.models.account import Account
    from tenants.models.organization import Organization


def _get_account_by_public_id_in_organization(
    *,
    organization: Organization,
    public_id: uuid.UUID,
) -> Account | None:
    from accounts.models.account import Account

    return Account.records.filter(public_id=public_id, organization=organization).first()
