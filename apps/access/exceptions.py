"""Domain error codes for the access app."""

from core.exceptions import BaseAPIErrorCode


class PermissionDenied(BaseAPIErrorCode):
    code = "access_0001"
    detail = "You don't have permission to perform this action."


class RoleError:
    class NotFound(BaseAPIErrorCode):
        code = "role_0001"
        detail = "Role not found."

    class NameTaken(BaseAPIErrorCode):
        code = "role_0002"
        detail = "A role with this name already exists in this organization."

    class SystemRoleProtected(BaseAPIErrorCode):
        code = "role_0003"
        detail = "System roles cannot be modified or deleted."

    class UnknownPermissionCode(BaseAPIErrorCode):
        code = "role_0004"
        detail = "One or more permission codes are not registered."


class RoleAssignmentError:
    class NotFound(BaseAPIErrorCode):
        code = "role_assignment_0001"
        detail = "Role assignment not found."

    class CrossOrganization(BaseAPIErrorCode):
        code = "role_assignment_0002"
        detail = "Account and role must belong to the same organization."

    class AccountNotFound(BaseAPIErrorCode):
        code = "role_assignment_0003"
        detail = "Account not found in this organization."

    class LastOwner(BaseAPIErrorCode):
        code = "role_assignment_0004"
        detail = "Cannot remove the last Owner from an organization."


class SeedError:
    class PermissionsMissing(BaseAPIErrorCode):
        code = "access_0100"
        detail = "Required permissions are missing. Run `manage.py seed_rbac` first."
