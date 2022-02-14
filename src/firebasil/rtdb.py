from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional, Protocol, runtime_checkable
from urllib.parse import urljoin

import aiohttp
from aiohttp_sse_client import client as sse_client
from aiohttp_sse_client.client import MessageEvent

from firebasil.exceptions import RtdbListenerConnectionException, RtdbRequestException
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
        reconnection_time: Optional[timedelta] = None,
        max_connect_retry: Optional[int] = None,
    ) -> AsyncGenerator[RtdbListener, None]:
        listener = RtdbListener(_node=self, on_event=on_event)
        await listener.start_listening(
            reconnection_time=reconnection_time,
            max_connect_retry=max_connect_retry,
        )

        try:
            yield listener
        finally:
            await listener.stop_listening()


@runtime_checkable
class OnEvent(Protocol):
    def __call__(self, event: RtdbEvent) -> None:
        ...


@dataclass
class RtdbListener:
    _node: RtdbNode

    stream_consumer: Optional[asyncio.Task] = field(
        default=None,
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    #: Callable to trigger when an event is received
    on_event: OnEvent = field(repr=False)

    async def start_listening(
        self,
        reconnection_time: Optional[timedelta] = None,
        max_connect_retry: Optional[int] = None,
    ):
        opened = False
        errored = False

        connect_kwargs: Dict[str, Any] = {}
        if reconnection_time:
            connect_kwargs["reconnection_time"] = reconnection_time
        if max_connect_retry:
            connect_kwargs["max_connect_retry"] = max_connect_retry

        def handle_message(message: MessageEvent):
            logger.info("Message: %s", message)
            json_msg: Dict[str, Any] = json.loads(message.data)
            event = RtdbEvent(
                event=EventType[message.type],
                path=json_msg["path"],
                data=json_msg["data"],
            )
            self.on_event(event)

        def handle_open():
            nonlocal opened
            opened = True

        def handle_error():
            nonlocal errored
            errored = True

        async def listener_coro():
            url = urljoin(self._node._rtdb.database_url, self._node.json_url)
            headers = {
                **self._node._rtdb.session.headers,
                "Accept": "text/event-stream",
            }
            async with sse_client.EventSource(
                url,
                headers=headers,
                params=self._node.params,
                on_message=handle_message,
                on_open=handle_open,
                on_error=handle_error,
                **connect_kwargs,
            ) as event_source:
                async for event in event_source:
                    logger.debug(event)

        loop = asyncio.get_event_loop()
        self.stream_consumer = loop.create_task(listener_coro())
        while not opened and not errored:
            await asyncio.sleep(0)
        if errored:
            raise RtdbListenerConnectionException(
                f"Unable to listen to {self._node.json_url}"
            )

    async def stop_listening(self):
        self.stream_consumer.cancel()
        while not self.stream_consumer.cancelled():
            await asyncio.sleep(0)
        self.stream_consumer = None


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
