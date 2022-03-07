import pytest

from firebasil.auth import AuthClient
from firebasil.auth.types import SignInWithTokenUser, SignUpUser
from firebase_admin import auth as admin_auth, App
from firebase_admin._user_mgt import UserRecord


@pytest.mark.asyncio
async def test_create_and_delete_account(auth_client: AuthClient):
    """
    Can create user accounts, and delete them
    """
    user = await auth_client.sign_up("kevin@k2bd.dev", "password1")
    assert isinstance(user, SignUpUser)
    assert user.email == "kevin@k2bd.dev"


@pytest.mark.asyncio
async def test_sign_in_with_custom_token(auth_client: AuthClient, admin_app: App):
    """
    Can sign in with a server-issued custom token
    """
    created_user: UserRecord = admin_auth.create_user()
    token: bytes = admin_auth.create_custom_token(created_user.uid)

    user = await auth_client.sign_in_with_custom_token(token=token.decode("utf-8"))

    assert isinstance(user, SignInWithTokenUser)
