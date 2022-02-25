import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type, TypeVar

import aiohttp
from stringcase import snakecase

from firebasil.auth.types import (
    AnonymousUser,
    EmailProviders,
    RefreshUser,
    ResetResponse,
    SignInWithOauthUser,
    SignInWithPasswordUser,
    SignInWithTokenUser,
    SignUpUser,
    _Base,
)
from firebasil.exceptions import AuthRequestException
from firebasil.types import JSON

logger = logging.getLogger(__name__)

_B = TypeVar("_B", bound=_Base)


TOKEN_ROUTE = "token"
ACCOUNTS_ROUTE = "accounts"
SIGN_UP_ROUTE = ACCOUNTS_ROUTE + ":signUp"
SIGN_IN_PASSWORD_ROUTE = ACCOUNTS_ROUTE + ":signInWithPassword"
SIGN_IN_OAUTH_ROUTE = ACCOUNTS_ROUTE + ":signInWithIdp"
CREATE_AUTH_URI_ROUTE = ACCOUNTS_ROUTE + ":createAuthUri"
RESET_PASSWORD_ROUTE = ACCOUNTS_ROUTE + ":sendOobCode"

API_KEY_PARAM = "key"
EMAIL_PARAM = "email"
GRANT_TYPE_PARAM = "grant_type"
IDENTIFIER_PARAM = "identifier"
PASSWORD_PARAM = "password"
POST_BODY_PARAM = "postBody"
REFRESH_TOKEN_PARAM = "refresh_token"
REQUEST_TYPE_PARAM = "requestType"
REQUEST_URI_PARAM = "requestUri"
RETURN_IDP_CREDENTIAL_PARAM = "returnIdpCredential"
RETURN_SECURE_TOKEN_PARAM = "returnSecureToken"
TOKEN_PARAM = "token"

PASSWORD_RESET_REQUEST_TYPE = "PASSWORD_RESET"
REFRESH_TOKEN_GRANT_TYPE = "refresh_token"

LOCALE_HEADER = "X-Firebase-Locale"


def snakeify_dict_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    return {snakecase(key): value for key, value in data.items()}


def return_secure_token():
    return {RETURN_SECURE_TOKEN_PARAM: True}


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
    identity_toolkit_url: str

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
        id_token: str,
        provider_id: str,
        return_idp_credential: bool,
    ):
        """
        Sign in with an OAuth credential
        """
        post_body = f"id_token=[{id_token}]&providerId=[{provider_id}]"
        body = {
            REQUEST_URI_PARAM: request_uri,
            POST_BODY_PARAM: post_body,
            **return_secure_token(),
            RETURN_IDP_CREDENTIAL_PARAM: return_idp_credential,
        }
        return await self._post_model(
            route=SIGN_IN_OAUTH_ROUTE,
            body=body,
            model=SignInWithOauthUser,
        )

    async def get_associated_providers(self, email: str):
        """
        Get OAuth providers associated with a given email
        """
        body = {IDENTIFIER_PARAM: f"[{email}]"}
        return await self._post_model(
            route=CREATE_AUTH_URI_ROUTE,
            body=body,
            model=EmailProviders,
        )

    async def send_password_reset_email(self, email: str, locale: Optional[str]):
        """
        Send a password reset email to the given email.

        Optionally, a locale string can be passed to localize the password
        reset email.
        """
        body = {REQUEST_TYPE_PARAM: PASSWORD_RESET_REQUEST_TYPE, EMAIL_PARAM: email}
        headers = {LOCALE_HEADER: locale} if locale else None
        return await self._post_model(
            route=RESET_PASSWORD_ROUTE,
            body=body,
            headers=headers,
            model=ResetResponse,
        )
