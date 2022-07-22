from typing import Any, Dict, Type


class FirebasilException(Exception):
    """
    Base exception for firebasil
    """


class AuthException(FirebasilException):
    """
    An issue with auth
    """


class AuthRequestException(AuthException):
    """
    An issue with a network request to auth
    """


class InvalidCustomToken(AuthRequestException):
    """
    The custom token format is incorrect or the token is invalid for some
    reason (e.g. expired, invalid signature etc.)
    """


class CredentialMismatch(AuthRequestException):
    """The custom token corresponds to a different Firebase project."""


class TokenExpired(AuthRequestException):
    """The user's credential is no longer valid. The user must sign in again."""


class UserDisabled(AuthRequestException):
    """The user account has been disabled by an administrator."""


class UserNotFound(AuthRequestException):
    """
    The user corresponding to the refresh token was not found.
    It is likely the user was deleted.
    """


class InvalidRefreshToken(AuthRequestException):
    """An invalid refresh token is provided."""


class InvalidGrantType(AuthRequestException):
    """the grant type specified is invalid."""


class MissingRefreshToken(AuthRequestException):
    """no refresh token provided."""


class EmailExists(AuthRequestException):
    """The email address is already in use by another account."""


class OperationNotAllowed(AuthRequestException):
    """Password sign-in is disabled for this project."""


class TooManyAttemptsTryLater(AuthRequestException):
    """
    We have blocked all requests from this device due to unusual activity.
    Try again later.
    """


class EmailNotFound(AuthRequestException):
    """
    There is no user record corresponding to this identifier.
    The user may have been deleted.
    """


class InvalidPassword(AuthRequestException):
    """The password is invalid or the user does not have a password."""


class InvalidIdpResponse(AuthRequestException):
    """The supplied auth credential is malformed or has expired."""


class InvalidEmail(AuthRequestException):
    """The email address is badly formatted."""


class ExpiredOobCode(AuthRequestException):
    """The action code has expired."""


class InvalidOobCode(AuthRequestException):
    """
    The action code is invalid. This can happen if the code is malformed,
    expired, or has already been used.
    """


class InvalidIdToken(AuthRequestException):
    """he user's credential is no longer valid. The user must sign in again."""


class WeakPassword(AuthRequestException):
    """The password must be 6 characters long or more."""


class CredentialTooOldLoginAgain(AuthRequestException):
    """The user's credential is no longer valid. The user must sign in again."""


class FederatedUserIdAlreadyLinked(AuthRequestException):
    """This credential is already associated with a different user account."""


AUTH_REQUEST_EXCEPTION_MAPPING = {
    "INVALID_CUSTOM_TOKEN": InvalidCustomToken,
    "CREDENTIAL_MISMATCH": CredentialMismatch,
    "TOKEN_EXPIRED": TokenExpired,
    "USER_DISABLED": UserDisabled,
    "USER_NOT_FOUND": UserNotFound,
    "INVALID_REFRESH_TOKEN": InvalidRefreshToken,
    "INVALID_GRANT_TYPE": InvalidGrantType,
    "MISSING_REFRESH_TOKEN": MissingRefreshToken,
    "EMAIL_EXISTS": EmailExists,
    "OPERATION_NOT_ALLOWED": OperationNotAllowed,
    "TOO_MANY_ATTEMPTS_TRY_LATER": TooManyAttemptsTryLater,
    "EMAIL_NOT_FOUND": EmailNotFound,
    "INVALID_PASSWORD": InvalidPassword,
    "INVALID_IDP_RESPONSE": InvalidIdpResponse,
    "INVALID_EMAIL": InvalidEmail,
    "EXPIRED_OOB_CODE": ExpiredOobCode,
    "INVALID_OOB_CODE": InvalidOobCode,
    "INVALID_ID_TOKEN": InvalidIdToken,
    "WEAK_PASSWORD": WeakPassword,
    "CREDENTIAL_TOO_OLD_LOGIN_AGAIN": CredentialTooOldLoginAgain,
    "FEDERATED_USER_ID_ALREADY_LINKED": FederatedUserIdAlreadyLinked,
}


def get_auth_request_exception(body: Dict[str, Any]) -> Type[AuthRequestException]:
    """
    Get the appropriate auth exception for a given error message body, falling
    back to the base ``AuthRequestException``
    """
    if not isinstance(body, dict):
        return AuthRequestException

    err = body.get("error")
    if not isinstance(err, dict):
        return AuthRequestException

    message = err.get("message")
    if not isinstance(message, str):
        return AuthRequestException

    for key, exception in AUTH_REQUEST_EXCEPTION_MAPPING.items():
        if message.startswith(key):
            return exception
    else:
        return AuthRequestException


class RtdbException(FirebasilException):
    """
    An issue with the realtime database
    """


class RtdbRequestException(RtdbException):
    """
    An issue with a network request to the realtime database
    """


class RtdbEventStreamException(RtdbException):
    """
    Error connecting to the RTDB Listener
    """
