"""Domain error codes for the accounts app."""

from core.exceptions import BaseAPIErrorCode


class RegistrationError:
    class EmailTaken(BaseAPIErrorCode):
        code = "registration_0001"
        detail = "An account with this email already exists."

    class SlugTaken(BaseAPIErrorCode):
        code = "registration_0002"
        detail = "An organization with this slug already exists."


class LoginError:
    class InvalidCredentials(BaseAPIErrorCode):
        code = "login_0001"
        detail = "Invalid email or password."

    class InactiveUser(BaseAPIErrorCode):
        code = "login_0002"
        detail = "This user is inactive."

    class NoActiveAccount(BaseAPIErrorCode):
        code = "login_0003"
        detail = "No active account found for this user."


class AccountSwitchError:
    class NotFound(BaseAPIErrorCode):
        code = "switch_0001"
        detail = "Account not found."

    class NotActive(BaseAPIErrorCode):
        code = "switch_0002"
        detail = "That account is not active."
