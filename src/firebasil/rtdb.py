from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from typing_extensions import Protocol, runtime_checkable

from firebasil.exceptions import RtdbListenerConnectionException, RtdbRequestException
from firebasil.sse.SseClient import SseClient, SseMessage
from firebasil.types import JSON

logger = logging.getLogger(__name__)

STARTUP_TIME_SECONDS = 0.5


class EventType(str, Enum):
    put = "put"
    patch = "patch"
    keep_alive = "keep-alive"
    cancel = "cancel"
    auth_revoked = "auth_revoked"


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

    #: Refresh token. If provided, expired tokens will be refreshed
    #: automatically. (optional)
    refresh_token: Optional[str] = None  # TODO

    #: Access token, for example for service accounts (optional)
    access_token: Optional[str] = None  # TODO

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

        if self.access_token:
            logger.info("Using service account credentials.")
            headers["Authorization"] = f"Bearer {self.access_token}"

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
    """
    A node within the realtime database
    """

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

    async def push(self, data: JSON) -> str:
        """
        Push data into a list, returning the ID of the new node.

        See https://firebase.google.com/docs/database/web/lists-of-data
        """
        async with self._rtdb.session.post(
            self.json_url,
            params=self.params,
            json=data,
        ) as response:
            self._handle_request_error(response, "post")
            result = await response.json()
            return result["name"]

    async def update(self, data: JSON) -> JSON:
        """
        Update data at a given location with new JSON.

        See https://firebase.google.com/docs/database/web/read-and-write#updating_or_deleting_data
        """  # noqa: E501
        async with self._rtdb.session.patch(
            self.json_url,
            params=self.params,
            json=data,
        ) as response:
            self._handle_request_error(response, "patch")
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

    @asynccontextmanager
    async def listen(
        self,
        on_event: OnEvent,
    ) -> AsyncGenerator[None, None]:
        def on_message(message: SseMessage):
            logger.info("Message: %s", message)
            event = RtdbEvent(
                event=EventType[message.event],
                path=message.data["path"],
                data=message.data["data"],
            )
            on_event(event)

        async with SseClient(
            url=urljoin(self._rtdb.database_url, self.json_url),
            headers=self._rtdb.session.headers,
            params=self.params,
            on_message=on_message,
        ):
            yield None

@runtime_checkable
class OnEvent(Protocol):
    def __call__(self, event: RtdbEvent) -> None:
        ...

@dataclass
class RtdbEvent:
    """
    An event from the realtime database
    """

    #: Type of event
    event: EventType

    #: Path of the event, relative to the listener
    path: str

    #: Body of the event, either the new or updated values
    data: JSON

    #: Time the event was received (UTC, with tzinfo)
    time_received: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
