from typing import AsyncGenerator

import pytest

from firebasil.rtdb import Rtdb, RtdbNode
from tests.integration.constants import TESTING_DATABASE_URL


@pytest.fixture
async def rtdb_root() -> AsyncGenerator[RtdbNode, None]:
    async with Rtdb(database_url=TESTING_DATABASE_URL) as root:
        try:
            yield root
        finally:
            # TODO: clear database
            await root.delete()
