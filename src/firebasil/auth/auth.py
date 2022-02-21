import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import aiohttp
from stringcase import snakecase

from firebasil.auth.types import RefreshUser, SignInWithTokenUser, SignUpUser
from firebasil.exceptions import AuthRequestException

logger = logging.getLogger(__name__)


ACCOUNTS_ROUTE = "accounts"
TOKEN_ROUTE = "token"
SIGN_UP_ROUTE = ACCOUNTS_ROUTE + ":signUp"
SIGN_IN_PASSWORD_ROUTE = ACCOUNTS_ROUTE + ":signInWithPassword"

RETURN_SECURE_TOKEN_PARAM = "returnSecureToken"

ID_TOKEN_FIELD = "idToken"
REFRESH_TOKEN_FIELD = "refreshToken"
EXPIRES_IN_FIELD = "expiresIn"
EMAIL_FIELD = "email"
LOCAL_ID_FIELD = "localId"


def snakeify_dict_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    return {snakecase(key): value for key, value in data.items()}


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
        return {"key": self.api_key}

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

    async def _post(self, route, body):
        async with self.session.post(
            route,
            params=self.params,
            json=body,
        ) as response:
            self._handle_request_error(response)
            return await response.json()

    async def sign_in_with_custom_token(self, token: str):
        body = {"token": token, RETURN_SECURE_TOKEN_PARAM: True}
        user_data = await self._post(ACCOUNTS_ROUTE, body)
        return SignInWithTokenUser(**snakeify_dict_keys(user_data))

    async def refresh(self, refresh_token: str):
        """
        Trade a refresh token for a new ID token
        """
        body = {"refresh_token": refresh_token, "grant_type": "refresh_token"}
        user_data = await self._post(TOKEN_ROUTE, body)
        return RefreshUser(**snakeify_dict_keys(user_data))

    async def sign_up(self, email: str, password: str):
        """
        Sign up a new user
        """
        body = {"email": email, "password": password, RETURN_SECURE_TOKEN_PARAM: True}
        user_data = await self._post(SIGN_UP_ROUTE, body)
        return SignUpUser(**snakeify_dict_keys(user_data))

    async def sign_in_with_password(self, email: str, password: str):
        """
        Sign in with email and password
        """
        body = {"email": email, "password": password, RETURN_SECURE_TOKEN_PARAM: True}
        user_data = await self._post(SIGN_IN_PASSWORD_ROUTE, body)
