import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar
from urllib.parse import urljoin

import aiohttp
from stringcase import snakecase

from firebasil.auth.types import (
    AccountInfo,
    AnonymousUser,
    ChangeEmailResponse,
    ChangePasswordResponse,
    ConfirmEmailVerificationResponse,
    EmailProviders,
    EmulatorConfigurtion,
    EmulatorOobCodes,
    EmulatorSmsCodes,
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

PRODUCTION_IDENTITY_TOOLKIT_URL = "https://identitytoolkit.googleapis.com/"
VERSION_ONE_API_ROUTE = "v1"

ACCOUNTS_ROUTE = "accounts"
CREATE_AUTH_URI_ROUTE = ACCOUNTS_ROUTE + ":createAuthUri"
DELETE_ACCOUNT_ROUTE = ACCOUNTS_ROUTE + ":delete"
OUT_OF_BAND_CODES_ROUTE = ACCOUNTS_ROUTE + ":sendOobCode"
RESET_PASSWORD_CODE_ROUTE = ACCOUNTS_ROUTE = ":resetPassword"
SIGN_IN_OAUTH_ROUTE = ACCOUNTS_ROUTE + ":signInWithIdp"
SIGN_IN_PASSWORD_ROUTE = ACCOUNTS_ROUTE + ":signInWithPassword"
SIGN_UP_ROUTE = ACCOUNTS_ROUTE + ":signUp"
TOKEN_ROUTE = "token"
UPDATE_ACCOUNT_ROUTE = ACCOUNTS_ROUTE = ":update"
USER_DATA_ROUTE = ACCOUNTS_ROUTE + ":lookup"

API_KEY_PARAM = "key"
CONTINUE_URI_PARAM = "continueUri"
DELETE_ATTRIBUTE_PARAM = "deleteAttribute"
DELETE_PROVIDER_PARAM = "deleteProvider"
DISPLAY_NAME_PARAM = "displayName"
EMAIL_PARAM = "email"
GRANT_TYPE_PARAM = "grant_type"
ID_TOKEN_PARAM = "idToken"
IDENTIFIER_PARAM = "identifier"
NEW_PASSWORD_PARAM = "newPassword"
OUT_OF_BAND_CODE_PARAM = "oobCode"
PASSWORD_PARAM = "password"
PHOTO_URL_PARAM = "photoUrl"
POST_BODY_PARAM = "postBody"
REFRESH_TOKEN_PARAM = "refresh_token"
REQUEST_TYPE_PARAM = "requestType"
REQUEST_URI_PARAM = "requestUri"
RETURN_IDP_CREDENTIAL_PARAM = "returnIdpCredential"
RETURN_SECURE_TOKEN_PARAM = "returnSecureToken"
TOKEN_PARAM = "token"

PASSWORD_RESET_REQUEST_TYPE = "PASSWORD_RESET"
REFRESH_TOKEN_GRANT_TYPE = "refresh_token"
VERIFY_EMAIL_REQUEST_TYPE = "VERIFY_EMAIL"

DISPLAY_NAME_DELETE_VALUE = "DISPLAY_NAME"
PHOTO_URL_DELETE_VALUE = "PHOTO_URL"

LOCALE_HEADER = "X-Firebase-Locale"


def snakeify_dict_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert (nested) JSON keys to snake case
    """

    def snakeify_value(val: JSON):
        if isinstance(val, dict):
            return snakeify_dict_keys(val)
        elif isinstance(val, list):
            return [snakeify_value(subval) for subval in val]
        else:
            return val

    return {snakecase(key): snakeify_value(value) for key, value in data.items()}


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
        user = await auth_client.sign_in_with_custom_token(key=...)
    ```
    """

    #: URL of the identity toolkit to use
    identity_toolkit_url: str = PRODUCTION_IDENTITY_TOOLKIT_URL

    #: Optional API key to use in requests
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

    @staticmethod
    def _session(base_url: str):
        headers = {"Content-Type": "application/json"}
        return aiohttp.ClientSession(
            base_url=base_url,
            headers=headers,
        )

    async def __aenter__(self):
        self.session = self._session(
            base_url=urljoin(self.identity_toolkit_url, VERSION_ONE_API_ROUTE)
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
        self,
        route: str,
        body: JSON,
        headers: Optional[Dict[str, str]] = None,
    ) -> JSON:
        """
        Post, and return the JSON or raise for an error code.
        """
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
        """
        Sign a user in with a custom token.
        """
        body = {TOKEN_PARAM: token, **return_secure_token()}
        return await self._post_model(
            route=ACCOUNTS_ROUTE,
            body=body,
            model=SignInWithTokenUser,
        )

    async def refresh(self, refresh_token: str):
        """
        Trade a refresh token for a new ID token.
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
        Sign up a new user.
        """
        body = {EMAIL_PARAM: email, PASSWORD_PARAM: password, **return_secure_token()}
        return await self._post_model(
            route=SIGN_UP_ROUTE,
            body=body,
            model=SignUpUser,
        )

    async def sign_in_with_password(self, email: str, password: str):
        """
        Sign in with email and password.
        """
        body = {EMAIL_PARAM: email, PASSWORD_PARAM: password, **return_secure_token()}
        return await self._post_model(
            route=SIGN_IN_PASSWORD_ROUTE,
            body=body,
            model=SignInWithPasswordUser,
        )

    async def sign_in_anonymous(self):
        """
        Sign in anonymously.
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
        Sign in with an OAuth credential.
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
        Get OAuth providers associated with a given email.
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
            route=OUT_OF_BAND_CODES_ROUTE,
            body=body,
            headers=headers,
            model=ResetResponse,
        )

    async def verify_password_reset_code(self, reset_code: str):
        """
        Verify the code sent via a password reset email.
        """
        body = {OUT_OF_BAND_CODE_PARAM: reset_code}
        return await self._post_model(
            route=RESET_PASSWORD_CODE_ROUTE,
            body=body,
            model=VerifyResetResponse,
        )

    async def confirm_password_reset(self, reset_code: str, new_password: str):
        """
        Set a new password after the reset code is confirmed.
        """
        body = {OUT_OF_BAND_CODE_PARAM: reset_code, NEW_PASSWORD_PARAM: new_password}
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
        Update or remove a user's display name and/or photo.
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
        Get information about a user.
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
        Associate an email and password with a given user.
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
        Unlink an account from the given provider IDs.
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
            route=OUT_OF_BAND_CODES_ROUTE,
            body=body,
            headers=headers,
            model=SendEmailVerificationResponse,
        )

    async def confirm_email_verification(self, code: str):
        """
        Confirm the email verification code sent to the user.
        """
        body = {OUT_OF_BAND_CODE_PARAM: code}
        return await self._post_model(
            route=UPDATE_ACCOUNT_ROUTE,
            body=body,
            model=ConfirmEmailVerificationResponse,
        )

    async def delete_account(self, id_token: str) -> None:
        """
        Delete an account.
        """
        body = {ID_TOKEN_PARAM: id_token}
        await self._post(
            route=DELETE_ACCOUNT_ROUTE,
            body=body,
        )

    # -- Emulator methods

    def _emulator_session(self):
        emulator_route = urljoin(self.identity_toolkit_url, "emulator")
        return self._session(base_url=urljoin(emulator_route, VERSION_ONE_API_ROUTE))

    async def emulator_clear_accounts(self, project_id: str):
        """
        Remove all user accounts.

        Only available for the auth emulator.
        """
        async with self._emulator_session().delete(
            f"projects/{project_id}/accounts",
        ) as response:
            self._handle_request_error(response)

    async def emulator_get_configuration(self, project_id: str):
        """
        Get emulator configuration.

        Only available for the auth emulator.
        """
        async with self._emulator_session().get(
            f"projects/{project_id}/config",
        ) as response:
            self._handle_request_error(response)
            result = await response.json()
            EmulatorConfigurtion(**snakeify_dict_keys(result))

    async def emulator_update_configuration(
        self, project_id: str, allow_duplicate_emails: bool
    ):
        """
        Update the emulator configuration.

        Only available for the auth emulator.
        """
        body = {"signIn": {"allowDuplicateEmails": allow_duplicate_emails}}
        async with self._emulator_session().patch(
            f"projects/{project_id}/config",
            body=body,
        ) as response:
            self._handle_request_error(response)
            result = await response.json()
            EmulatorConfigurtion(**snakeify_dict_keys(result))

    async def emulator_get_out_of_band_codes(self, project_id: str):
        """
        Get out-of-band codes sent to an auth emulator.

        Only available for the auth emulator.
        """
        async with self._emulator_session().get(
            f"projects/{project_id}/oobCodes",
        ) as response:
            self._handle_request_error(response)
            result = await response.json()
            EmulatorOobCodes(**snakeify_dict_keys(result))

    async def emulator_get_sms_codes(self, project_id: str):
        """
        Get SMS verification codes sent to an auth emulator.

        Only available for the auth emulator.
        """
        async with self._emulator_session().get(
            f"projects/{project_id}/verificationCodes",
        ) as response:
            self._handle_request_error(response)
            result = await response.json()
            EmulatorSmsCodes(**snakeify_dict_keys(result))
