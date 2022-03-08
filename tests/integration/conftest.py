from typing import AsyncGenerator
from uuid import uuid4

import pytest
from firebase_admin import App, initialize_app

from firebasil.auth import AuthClient
from firebasil.auth.constants import FIREBASE_AUTH_EMULATOR_HOST
from firebasil.auth.types import SignUpUser
from firebasil.rtdb import Rtdb, RtdbNode
from tests.integration.constants import (
    EXAMPLE_USER_PASSWORD,
    TESTING_DATABASE_URL,
    TESTING_PROJECT_ID,
)

# Initialize the admin app once
_admin_app = initialize_app(options={"projectId": TESTING_PROJECT_ID})


@pytest.fixture
async def rtdb_root() -> AsyncGenerator[RtdbNode, None]:
    async with Rtdb(database_url=TESTING_DATABASE_URL) as root:
        try:
            yield root
        finally:
            await root.delete()


@pytest.fixture
async def auth_client() -> AsyncGenerator[AuthClient, None]:
    if not FIREBASE_AUTH_EMULATOR_HOST:
        raise RuntimeError(
            "Please set the FIREBASE_AUTH_EMULATOR_HOST environment variable"
        )
    async with AuthClient(api_key="any-fake-key") as auth_client:
        initial_settings = await auth_client.emulator_get_configuration(
            TESTING_PROJECT_ID
        )
        try:
            yield auth_client
        finally:
            # Rest emulator state
            await auth_client.emulator_clear_accounts(TESTING_PROJECT_ID)
            await auth_client.emulator_update_configuration(
                TESTING_PROJECT_ID,
                initial_settings.sign_in.allow_duplicate_emails,
            )


@pytest.fixture
async def example_user(auth_client: AuthClient) -> SignUpUser:
    """
    Create a user with a random email
    """
    user_email = str(uuid4()) + "@k2bd.dev"
    return await auth_client.sign_up(user_email, EXAMPLE_USER_PASSWORD)


@pytest.fixture
def admin_app() -> App:
    return _admin_app
