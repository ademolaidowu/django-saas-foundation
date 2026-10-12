from core.models.base import BaseTextChoices


class AccountStatus(BaseTextChoices):
    """
    Lifecycle state of an `Account`.

    - INVITED: created by an admin, user has not accepted yet. Not used in
      Phase 2 (no invitation flow); reserved for a future invitation feature.
    - ACTIVE: default state after registration or invite acceptance. The only
      status login accepts.
    - SUSPENDED: admin-disabled. Authentication rejects tokens on these
      accounts without destroying them.
    """

    INVITED = "invited", "Invited"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
