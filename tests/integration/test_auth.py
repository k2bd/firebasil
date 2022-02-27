from datetime import timedelta
import pytest

from firebasil.auth import AuthClient
from firebasil.auth.types import SignUpUser

@pytest.mark.asyncio
async def test_create_and_delete_account(auth_client: AuthClient):
    """
    Can create user accounts, and delete them
    """
    user = await auth_client.sign_up("kevin@k2bd.dev", "password1")
    assert user == SignUpUser("adsasd", "kevin@k2bd.dev", "asdasd", "asdasd", timedelta(seconds=123))
