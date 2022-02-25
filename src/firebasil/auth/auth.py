import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

import aiohttp
from stringcase import snakecase

from firebasil.auth.types import (
    AccountInfo,
    AnonymousUser,
    ChangeEmailResponse,
    ChangePasswordResponse,
    ConfirmEmailVerificationResponse,
    EmailProviders,
    LinkAccountEmailResponse,
    LinkAccountOauthResponse,
    RefreshUser,
    ResetResponse,
    SendEmailVerificationResponse,
    SignInWithOauthUser,
    SignInWithPasswordUser,
    SignInWithTokenUser,
    SignUpUser,
    UnlinkProviderResponse,
    UpdateProfileResponse,
    VerifyResetResponse,
    _Base,
)
from firebasil.exceptions import AuthRequestException
from firebasil.types import JSON

logger = logging.getLogger(__name__)

_B = TypeVar("_B", bound=_Base)

PRODUCTION_IDENTITY_TOOLKIT_URL = "https://identitytoolkit.googleapis.com/v1/"


TOKEN_ROUTE = "token"
ACCOUNTS_ROUTE = "accounts"
SIGN_UP_ROUTE = ACCOUNTS_ROUTE + ":signUp"
SIGN_IN_PASSWORD_ROUTE = ACCOUNTS_ROUTE + ":signInWithPassword"
SIGN_IN_OAUTH_ROUTE = ACCOUNTS_ROUTE + ":signInWithIdp"
CREATE_AUTH_URI_ROUTE = ACCOUNTS_ROUTE + ":createAuthUri"
SEND_RESET_PASSWORD_ROUTE = ACCOUNTS_ROUTE + ":sendOobCode"
RESET_PASSWORD_CODE_ROUTE = ACCOUNTS_ROUTE = ":resetPassword"
UPDATE_ACCOUNT_ROUTE = ACCOUNTS_ROUTE = ":update"
USER_DATA_ROUTE = ACCOUNTS_ROUTE + ":lookup"
DELETE_ACCOUNT_ROUTE = ACCOUNTS_ROUTE + ":delete"

API_KEY_PARAM = "key"
EMAIL_PARAM = "email"
GRANT_TYPE_PARAM = "grant_type"
IDENTIFIER_PARAM = "identifier"
PASSWORD_PARAM = "password"
POST_BODY_PARAM = "postBody"
CONTINUE_URI_PARAM = "continueUri"
REFRESH_TOKEN_PARAM = "refresh_token"
REQUEST_TYPE_PARAM = "requestType"
DELETE_PROVIDER_PARAM = "deleteProvider"
REQUEST_URI_PARAM = "requestUri"
RETURN_IDP_CREDENTIAL_PARAM = "returnIdpCredential"
RETURN_SECURE_TOKEN_PARAM = "returnSecureToken"
TOKEN_PARAM = "token"
RESET_CODE_PARAM = "oobCode"
NEW_PASSWORD_PARAM = "newPassword"
ID_TOKEN_PARAM = "idToken"
DISPLAY_NAME_PARAM = "displayName"
PHOTO_URL_PARAM = "photoUrl"
DELETE_ATTRIBUTE_PARAM = "deleteAttribute"

PASSWORD_RESET_REQUEST_TYPE = "PASSWORD_RESET"
VERIFY_EMAIL_REQUEST_TYPE = "VERIFY_EMAIL"
REFRESH_TOKEN_GRANT_TYPE = "refresh_token"

DISPLAY_NAME_DELETE_VALUE = "DISPLAY_NAME"
PHOTO_URL_DELETE_VALUE = "PHOTO_URL"

LOCALE_HEADER = "X-Firebase-Locale"


def snakeify_dict_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    return {snakecase(key): value for key, value in data.items()}


def return_secure_token():
    return {RETURN_SECURE_TOKEN_PARAM: True}


def post_body(id_token: str, provider_id: str):
    return f"id_token={id_token}&providerId={provider_id}"


@dataclass
class Auth:
    """
    A connection to Firebase auth. Should be used as an async context manager.

    ```python
    async with Auth(...) as auth_client:
        user_token = await auth_client.sign_in_with_custom_token(key=...)
    ```
    """

    #: URL of the identity toolkit to use
    identity_toolkit_url: str = PRODUCTION_IDENTITY_TOOLKIT_URL

    #: API key to use in requests
    api_key: Optional[str] = None

    session: aiohttp.ClientSession = field(
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    @property
    def params(self):
        return {API_KEY_PARAM: self.api_key} if self.api_key else {}

    async def __aenter__(self):
        headers = {"Content-Type": "application/json"}
        self.session = aiohttp.ClientSession(
            base_url=self.identity_toolkit_url,
            headers=headers,
        )

        return self

    async def __aexit__(self, *err):
        await self.session.close()

    def _handle_request_error(self, response: aiohttp.ClientResponse):
        try:
            response.raise_for_status()
        except Exception as e:
            msg = f"Error in {response.request_info.method} {response.request_info.url!r}: {str(e)}"  # noqa: E501
            raise AuthRequestException(msg) from e

    async def _post(
        self, route: str, body: JSON, headers: Optional[Dict[str, str]] = None
    ) -> JSON:
        headers = headers or {}
        async with self.session.post(
            route,
            params=self.params,
            json=body,
            headers=headers,
        ) as response:
            self._handle_request_error(response)
            return await response.json()

    async def _post_model(
        self,
        route: str,
        body: JSON,
        model: Type[_B],
        headers: Optional[Dict[str, str]] = None,
    ) -> _B:
        """
        Post, then convert the response to the given model
        """
        result = await self._post(
            route=route,
            body=body,
            headers=headers,
        )
        if isinstance(result, dict):
            return model(**snakeify_dict_keys(result))
        else:
            raise TypeError(f"Got unexpected response {type(result)}: {result}")

    async def sign_in_with_custom_token(self, token: str):
        body = {TOKEN_PARAM: token, **return_secure_token()}
        return await self._post_model(
            route=ACCOUNTS_ROUTE,
            body=body,
            model=SignInWithTokenUser,
        )

    async def refresh(self, refresh_token: str):
        """
        Trade a refresh token for a new ID token
        """
        body = {
            REFRESH_TOKEN_PARAM: refresh_token,
            GRANT_TYPE_PARAM: REFRESH_TOKEN_GRANT_TYPE,
        }
        return await self._post_model(
            route=TOKEN_ROUTE,
            body=body,
            model=RefreshUser,
        )

    async def sign_up(self, email: str, password: str):
        """
        Sign up a new user
        """
        body = {EMAIL_PARAM: email, PASSWORD_PARAM: password, **return_secure_token()}
        return await self._post_model(
            route=SIGN_UP_ROUTE,
            body=body,
            model=SignUpUser,
        )

    async def sign_in_with_password(self, email: str, password: str):
        """
        Sign in with email and password
        """
        body = {EMAIL_PARAM: email, PASSWORD_PARAM: password, **return_secure_token()}
        return await self._post_model(
            route=SIGN_IN_PASSWORD_ROUTE,
            body=body,
            model=SignInWithPasswordUser,
        )

    async def sign_in_anonymous(self):
        """
        Sign in anonymously
        """
        body = return_secure_token()
        return await self._post_model(
            route=SIGN_UP_ROUTE,
            body=body,
            model=AnonymousUser,
        )

    async def sign_in_with_oauth(
        self,
        request_uri: str,
        provider_token: str,
        provider_id: str,
        return_idp_credential: bool,
    ):
        """
        Sign in with an OAuth credential
        """
        body = {
            REQUEST_URI_PARAM: request_uri,
            POST_BODY_PARAM: post_body(
                id_token=provider_token, provider_id=provider_id
            ),
            **return_secure_token(),
            RETURN_IDP_CREDENTIAL_PARAM: return_idp_credential,
        }
        return await self._post_model(
            route=SIGN_IN_OAUTH_ROUTE,
            body=body,
            model=SignInWithOauthUser,
        )

    async def get_associated_providers(self, email: str, continue_uri: str):
        """
        Get OAuth providers associated with a given email
        """
        body = {IDENTIFIER_PARAM: email, CONTINUE_URI_PARAM: continue_uri}
        return await self._post_model(
            route=CREATE_AUTH_URI_ROUTE,
            body=body,
            model=EmailProviders,
        )

    async def send_password_reset_email(self, email: str, locale: Optional[str] = None):
        """
        Send a password reset email to the given email.

        Optionally, a locale string can be passed to localize the password
        reset email.
        """
        body = {REQUEST_TYPE_PARAM: PASSWORD_RESET_REQUEST_TYPE, EMAIL_PARAM: email}
        headers = {LOCALE_HEADER: locale} if locale else None
        return await self._post_model(
            route=SEND_RESET_PASSWORD_ROUTE,
            body=body,
            headers=headers,
            model=ResetResponse,
        )

    async def verify_password_reset_code(self, reset_code: str):
        """
        Verify the code sent via a password reset email.
        """
        body = {RESET_CODE_PARAM: reset_code}
        return await self._post_model(
            route=RESET_PASSWORD_CODE_ROUTE,
            body=body,
            model=VerifyResetResponse,
        )

    async def confirm_password_reset(self, reset_code: str, new_password: str):
        """
        Set a new password after the reset code is confirmed.
        """
        body = {RESET_CODE_PARAM: reset_code, NEW_PASSWORD_PARAM: new_password}
        return await self._post_model(
            route=RESET_PASSWORD_CODE_ROUTE,
            body=body,
            model=VerifyResetResponse,
        )

    async def change_email(
        self,
        id_token: str,
        new_email: str,
        locale: Optional[str] = None,
    ):
        """
        Change a user's email.

        Optionally, a locale string can be passed to localize the revocation
        email sent to the user.
        """
        body = {
            ID_TOKEN_PARAM: id_token,
            EMAIL_PARAM: new_email,
            **return_secure_token(),
        }
        headers = {LOCALE_HEADER: locale} if locale else None
        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            headers=headers,
            model=ChangeEmailResponse,
        )

    async def change_password(self, id_token: str, new_password: str):
        """
        Change a user's password.
        """
        body = {
            ID_TOKEN_PARAM: id_token,
            PASSWORD_PARAM: new_password,
            **return_secure_token(),
        }
        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            model=ChangePasswordResponse,
        )

    async def update_profile(
        self,
        id_token: str,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        delete_display_name: bool = False,
        delete_photo: bool = False,
    ):
        """
        Update or remove a user's display name and/or photo
        """
        body: Dict[str, Any] = {ID_TOKEN_PARAM: id_token, **return_secure_token()}
        if display_name:
            body[DISPLAY_NAME_PARAM] = display_name
        if photo_url:
            body[PHOTO_URL_PARAM] = photo_url
        delete_attributes = []
        if delete_display_name:
            delete_attributes.append(DISPLAY_NAME_DELETE_VALUE)
        if delete_photo:
            delete_attributes.append(PHOTO_URL_DELETE_VALUE)
        if delete_attributes:
            body[DELETE_ATTRIBUTE_PARAM] = delete_attributes

        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            model=UpdateProfileResponse,
        )

    async def get_user_data(self, id_token: str):
        """
        Get information about a user
        """
        body = {ID_TOKEN_PARAM: id_token}
        return await self._post_model(
            route=USER_DATA_ROUTE,
            body=body,
            model=AccountInfo,
        )

    async def link_account_with_email_and_password(
        self, id_token: str, email: str, password: str
    ):
        """
        Associate an email and password with a given user
        """
        body = {
            ID_TOKEN_PARAM: id_token,
            EMAIL_PARAM: email,
            PASSWORD_PARAM: password,
            **return_secure_token(),
        }
        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            model=LinkAccountEmailResponse,
        )

    async def link_account_with_oauth_credential(
        self,
        id_token: str,
        request_uri: str,
        provider_token: str,
        provider_id: str,
        return_idp_credential: bool,
    ):
        """
        Associate an account with an OAuth credential.
        """
        body = {
            ID_TOKEN_PARAM: id_token,
            REQUEST_URI_PARAM: request_uri,
            POST_BODY_PARAM: post_body(
                id_token=provider_token, provider_id=provider_id
            ),
            **return_secure_token(),
            RETURN_IDP_CREDENTIAL_PARAM: return_idp_credential,
        }
        return await self._post_model(
            route=SIGN_IN_OAUTH_ROUTE,
            body=body,
            model=LinkAccountOauthResponse,
        )

    async def unlink_provider(self, id_token: str, provider_ids: List[str]):
        """
        Unlink an account from the given provider IDs
        """
        body = {ID_TOKEN_PARAM: id_token, DELETE_PROVIDER_PARAM: provider_ids}
        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            model=UnlinkProviderResponse,
        )

    async def send_email_verification(
        self, id_token: str, locale: Optional[str] = None
    ):
        """
        Send an email confirmation email to a user.

        Optionally, a locale string can be passed to localize the confirmation
        email sent to the user.
        """
        body = {ID_TOKEN_PARAM: id_token, REQUEST_TYPE_PARAM: VERIFY_EMAIL_REQUEST_TYPE}
        headers = {LOCALE_HEADER: locale} if locale else None
        return await self._post_model(
            route=SEND_RESET_PASSWORD_ROUTE,
            body=body,
            headers=headers,
            model=SendEmailVerificationResponse,
        )

    async def confirm_email_verification(self, code: str):
        """
        Confirm the email verification code sent to the user.
        """
        body = {RESET_CODE_PARAM: code}
        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            model=ConfirmEmailVerificationResponse,
        )

    async def delete_account(self, id_token: str) -> None:
        body = {ID_TOKEN_PARAM: id_token}
        await self._post(
            route=DELETE_ACCOUNT_ROUTE,
            body=body,
        )
