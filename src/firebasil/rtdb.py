from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from typing_extensions import Protocol, runtime_checkable

from firebasil.exceptions import RtdbRequestException
from firebasil.sse.sse_client import SseClient, SseMessage
from firebasil.types import JSON

logger = logging.getLogger(__name__)

STARTUP_TIME_SECONDS = 0.5

ORDER_BY_KEY = "$key"
ORDER_BY_VALUE = "$value"
ORDER_BY_PRIORITY = "$priority"
EXPORT_FORMAT = "export"


class EventType(str, Enum):
    put = "put"
    patch = "patch"
    keep_alive = "keep-alive"
    cancel = "cancel"
    auth_revoked = "auth_revoked"


class SizeLimit(str, Enum):
    tiny = "tiny"
    small = "small"
    medium = "medium"
    large = "large"
    unlimited = "unlimited"


@dataclass
class Rtdb:
    """
    A connection to a realtime database. Should be used as an async context
    manager, which yields the root ``RtdbNode`` of the database.
    """

    #: URL of the realtime database, including schema
    database_url: str

    #: User ID token (optional)
    id_token: Optional[str] = None

    #: Access token, for example for service accounts (optional)
    access_token: Optional[str] = None

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

    def _handle_request_error(self, response: aiohttp.ClientResponse):
        try:
            response.raise_for_status()
        except Exception as e:
            msg = f"Error in {response.request_info.method} /{self.path}: {str(e)}"
            raise RtdbRequestException(msg) from e

    async def get(self) -> JSON:
        """
        Get the value of a node
        """
        async with self._rtdb.session.get(
            self.json_url,
            params=self.params,
        ) as response:
            self._handle_request_error(response)
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
            self._handle_request_error(response)
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
            self._handle_request_error(response)
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
            self._handle_request_error(response)
            return await response.json()

    async def delete(self) -> None:
        """
        Remove the value of a node, and all sub-nodes
        """
        async with self._rtdb.session.delete(
            self.json_url,
            params=self.params,
        ) as response:
            self._handle_request_error(response)
            return await response.json()

    def _copy_with_params(self, **kwargs) -> RtdbNode:
        query_params = {**(self.query_params or {})}
        query_params.update(kwargs)
        return type(self)(
            _rtdb=self._rtdb,
            path=self.path,
            query_params=query_params,
        )

    def order_by_key(self) -> RtdbNode:
        """
        Order filtering operations by key.

        Note, this does not order results, as they are returned as unordered
        JSON.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-ordered-data
        """  # noqa: E501
        return self.order_by(ORDER_BY_KEY)

    def order_by_value(self) -> RtdbNode:
        """
        Order filtering operations by node value.

        Note, this does not order results, as they are returned as unordered
        JSON.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-ordered-data
        """  # noqa: E501
        return self.order_by(ORDER_BY_VALUE)

    def order_by_priority(self) -> RtdbNode:
        """
        Order filtering operations by priority.

        Note, this does not order results, as they are returned as unordered
        JSON.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-ordered-data
        """  # noqa: E501
        return self.order_by(ORDER_BY_PRIORITY)

    def order_by(self, child_location: str) -> RtdbNode:
        """
        Order filtering operations by the value of a specified (possibly
        nested) child node.

        Note, this does not order results, as they are returned as unordered
        JSON.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-ordered-data
        """  # noqa: E501
        return self._copy_with_params(orderBy=f'"{child_location}"')

    def limit_to_first(self, limit: int) -> RtdbNode:
        """
        Only return the first ``limit`` results after some ordering and
        filtering is applied.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-filtering
        """  # noqa: E501
        return self._copy_with_params(limitToFirst=str(limit))

    def limit_to_last(self, limit: int) -> RtdbNode:
        """
        Only return the last ``limit`` results after some ordering and
        filtering is applied.
        """
        return self._copy_with_params(limitToLast=str(limit))

    def start_at(self, value: Any) -> RtdbNode:
        """
        Return values starting at ``value`` under some ordering.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-filtering
        """  # noqa: E501
        return self._copy_with_params(
            startAt=f'"{value}"' if isinstance(value, str) else value
        )

    def end_at(self, value: Any) -> RtdbNode:
        """
        Return values ending at ``value`` under some ordering.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-filtering
        """  # noqa: E501
        return self._copy_with_params(
            endAt=f'"{value}"' if isinstance(value, str) else value
        )

    def equal_to(self, value: Any) -> RtdbNode:
        """
        Return values with value equal to ``value`` under some ordering.

        See https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-filtering
        """  # noqa: E501
        return self._copy_with_params(
            equalTo=f'"{value}"' if isinstance(value, str) else value
        )

    def shallow(self) -> RtdbNode:
        """
        Create a node that only gets shallow data

        See https://firebase.google.com/docs/reference/rest/database#section-param-shallow
        """  # noqa: E501
        return self._copy_with_params(shallow="true")

    def export_format(self) -> RtdbNode:
        """
        Include priority data in responses

        See https://firebase.google.com/docs/reference/rest/database#section-param-format
        """  # noqa: E501
        return self._copy_with_params(format=EXPORT_FORMAT)

    def timeout(self, timeout: timedelta) -> RtdbNode:
        """
        Set a request timeout.

        See https://firebase.google.com/docs/reference/rest/database#section-param-timeout
        """  # noqa: E501
        timeout_str = f"{timeout.total_seconds()}s"
        return self._copy_with_params(timeout=timeout_str)

    def write_size_limit(self, limit: SizeLimit) -> RtdbNode:
        """
        Limit write sizes.

        See https://firebase.google.com/docs/reference/rest/database#section-param-writesizelimit
        """  # noqa: E501
        return self._copy_with_params(writeSizeLimit=limit.value)

    @asynccontextmanager
    async def events(self) -> AsyncGenerator[asyncio.Queue[RtdbEvent], None]:
        """
        Async context manager that listens to the event stream of this node and
        adds events to the async queue that it yields.
        """
        events: asyncio.Queue[RtdbEvent] = asyncio.Queue()

        async def on_message(message: SseMessage):
            logger.info("Message: %s", message)
            if message.data is None:
                event = RtdbEvent(event=EventType(message.event))
            elif isinstance(message.data, dict):
                event = RtdbEvent(
                    event=EventType(message.event),
                    path=message.data["path"],
                    data=message.data["data"],
                )
            else:
                raise ValueError(f"Could not parse event: {event}")

            await events.put(event)

        async with SseClient(
            url=urljoin(self._rtdb.database_url, self.json_url),
            headers=dict(self._rtdb.session.headers),
            params=self.params,
            on_message=on_message,
        ):
            yield events


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
    path: Optional[str] = None

    #: Body of the event, either the new or updated values
    data: Optional[JSON] = None
