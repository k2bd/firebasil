from typing import AsyncGenerator

import pytest

from firebasil.auth import AuthClient
from firebasil.auth.auth import EMULATOR_BASE_ROUTE
from firebasil.rtdb import Rtdb, RtdbNode
from tests.integration.constants import (
    TESTING_AUTH_URL,
    TESTING_DATABASE_URL,
    TESTING_PROJECT_ID,
)
from firebase_admin import initialize_app, delete_app, App


@pytest.fixture
async def rtdb_root() -> AsyncGenerator[RtdbNode, None]:
    async with Rtdb(database_url=TESTING_DATABASE_URL) as root:
        try:
            yield root
        finally:
            await root.delete()


@pytest.fixture
async def auth_client() -> AsyncGenerator[AuthClient, None]:
    async with AuthClient(
        identity_toolkit_url=TESTING_AUTH_URL,
        base_route=EMULATOR_BASE_ROUTE,
        api_key="any-fake-key",
    ) as auth_client:
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
def admin_app() -> App:
    app  = initialize_app(options={ "projectId": "demo-firebasil-test" })
    try:
        yield app
    finally:
        delete_app(app)
