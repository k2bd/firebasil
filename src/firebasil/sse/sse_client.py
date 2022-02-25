import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Dict, List, Optional

import aiohttp
from typing_extensions import Protocol, runtime_checkable

from firebasil.exceptions import RtdbEventStreamException
from firebasil.types import JSON


@dataclass
class SseMessage:
    event: str

    data: Optional[JSON] = None

    origin: Optional[str] = None

    last_event_id: Optional[str] = None


@runtime_checkable
class OnMessage(Protocol):
    def __call__(self, message: SseMessage) -> Awaitable[None]:
        ...


@runtime_checkable
class OnOpen(Protocol):
    def __call__(self) -> Awaitable[None]:
        ...


@runtime_checkable
class OnError(Protocol):
    def __call__(self) -> Awaitable[None]:
        ...


@dataclass
class SseClient:

    url: str

    on_message: OnMessage

    on_open: Optional[OnOpen] = None

    on_error: Optional[OnError] = None

    headers: Dict[str, str] = field(default_factory=dict)

    params: Dict[str, Any] = field(default_factory=dict)

    response: aiohttp.ClientResponse = field(
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    task: asyncio.Task = field(
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *err):
        await self.close()

    async def open(self):
        session = aiohttp.ClientSession(
            headers={
                **self.headers,
                "Accept": "text/event-stream",
            },
        )

        loop = asyncio.get_event_loop()

        try:
            self.response = await session.get(
                self.url,
                params=self.params,
            )
        except aiohttp.ClientConnectionError as e:
            if self.on_error:
                loop.create_task(self.on_error())
            raise RtdbEventStreamException(f"Unable to connect to {self.url}") from e

        try:
            self.response.raise_for_status()
        except Exception as e:
            if self.on_error:
                loop.create_task(self.on_error())
            raise RtdbEventStreamException(f"Bad response from {self.url}") from e

        async def listen_to_response():
            if self.on_open:
                loop.create_task(self.on_open())

            message_lines = []
            line_bytes = b""

            def emit_message(lines: List[str]):
                message_dict = {}
                for line in lines:
                    if not line:
                        continue
                    key_raw, value_raw = line.split(":", 1)
                    key = key_raw.strip()
                    value = value_raw.strip()
                    if key == "data":
                        message_dict["data"] = json.loads(value)
                    else:
                        message_dict[key] = value

                message = SseMessage(**message_dict)
                loop.create_task(self.on_message(message))

            async for new_bytes in self.response.content:
                if len(new_bytes):
                    line_bytes += new_bytes

                    try:
                        decoded_line = line_bytes.decode("utf-8")
                    except UnicodeError:
                        continue

                    if decoded_line.endswith("\n"):
                        # We have a complete line
                        line_bytes = b""
                        stripped_line = decoded_line.rstrip("\n")
                        message_lines.extend(stripped_line.split("\n"))
                        if decoded_line.endswith("\n\n") or decoded_line == "\n":
                            # Blank line present - message is complete
                            emit_message(message_lines)
                            message_lines = []

        self.task = loop.create_task(listen_to_response())

    async def close(self):
        self.response.close()
        self.task.cancel()
