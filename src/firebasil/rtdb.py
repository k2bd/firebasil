from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import aiohttp

from firebasil.exceptions import RtdbRequestException
from firebasil.types import JSON


@dataclass
class Rtdb:
    """
    A connection to a realtime database. Should be used as an async context
    manager, which yields the root node of the database:

    ```python
    async with Rtdb(...) as root:
        whole_database = await root.get()
    ```
    """

    #: URL of the realtime database, including schema
    database_url: str

    #: User ID token (optional)
    id_token: Optional[str] = None

    #: TODO service account creds

    session: aiohttp.ClientSession = field(
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    async def __aenter__(self):
        headers = {
            "Content-Type": "application/json",
        }

        self.session = aiohttp.ClientSession(
            base_url=self.database_url,
            headers=headers,
        )

        return RtdbNode(_rtdb=self)

    async def __aexit__(self, *err):
        await self.session.close()

    @property
    def auth_params(self) -> Dict[str, str]:
        return {"auth": self.id_token} if self.id_token else {}


@dataclass
class RtdbNode:

    _rtdb: Rtdb = field(
        repr=False,
        hash=False,
        compare=False,
    )

    #: Location of this node in the database
    path: str = ""

    query_params: Optional[Dict[str, Any]] = None

    @property
    def params(self) -> Dict[str, Any]:
        return {**(self.query_params or {}), **self._rtdb.auth_params}

    @property
    def json_url(self) -> str:
        return f"/{self.path}.json"

    def child(self, *path: str) -> RtdbNode:
        """
        Get a child of this node
        """
        added_path = "/".join(path)
        new_path = "/".join([self.path, added_path]) if self.path else added_path

        return type(self)(_rtdb=self._rtdb, path=new_path)

    def __truediv__(self, path: str) -> RtdbNode:
        """
        Enable getting child via /
        """
        return self.child(path)

    def _handle_request_error(self, response: aiohttp.ClientResponse, method: str):
        try:
            response.raise_for_status()
        except Exception as e:
            msg = f"Error in {method.upper()} {self.path!r}: {str(e)}"
            raise RtdbRequestException(msg) from e

    async def get(self) -> JSON:
        """
        Get the value of a node
        """
        async with self._rtdb.session.get(
            self.json_url,
            params=self.params,
        ) as response:
            self._handle_request_error(response, "get")
            return await response.json()

    async def set(self, data: JSON) -> JSON:
        """
        Set the value of a node
        """
        async with self._rtdb.session.put(
            self.json_url,
            params=self.params,
            json=data,
        ) as response:
            self._handle_request_error(response, "put")
            return await response.json()

    async def delete(self) -> None:
        """
        Remove the value of a node, and all sub-nodes
        """
        async with self._rtdb.session.delete(
            self.json_url,
            params=self.params,
        ) as response:
            self._handle_request_error(response, "delete")
            return await response.json()
