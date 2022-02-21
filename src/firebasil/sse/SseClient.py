import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp
from typing_extensions import Protocol, runtime_checkable

from firebasil.types import JSON


@dataclass
class SseMessage:
    event: str

    data: Optional[JSON] = None

    origin: Optional[str] = None

    last_event_id: Optional[str] = None


@runtime_checkable
class OnMessage(Protocol):
    def __call__(self, event: SseMessage) -> None:
        ...


@runtime_checkable
class OnOpen(Protocol):
    def __call__(self) -> None:
        ...


@runtime_checkable
class OnError(Protocol):
    def __call__(self) -> None:
        ...


@dataclass
class SseClient:

    url: str

    on_message: OnMessage

    on_open: Optional[OnOpen] = None

    on_error: Optional[OnError] = None

    headers: Dict[str, str] = field(default_factory=dict)

    params: Dict[str, Any] = field(default_factory=dict)

    _connection_task: Optional[asyncio.Task] = field(
        default=None,
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    _message_emitter_task: Optional[asyncio.Task] = field(
        default=None,
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
        queue = asyncio.Queue()

        opened = False
        errored = False

        async def connection():
            nonlocal opened
            nonlocal errored
            """
            Open the connection and consume events
            """
            sse_session = aiohttp.ClientSession(
                headers={
                    **self.headers,
                    "Accept": "text/event-stream",
                },
            )
            try:
                async with sse_session.get(
                    self.url,
                    params=self.params,
                ) as response:
                    opened = True
                    if self.on_open:
                        self.on_open()
                    while True:
                        new_bytes = response.content.read_nowait()
                        if len(new_bytes):
                            await queue.put(new_bytes)
                        await asyncio.sleep(0)
            except aiohttp.ClientConnectionError:
                errored = True
                if self.on_error:
                    self.on_error()
                raise

        async def message_emitter():
            """
            Take bytes from the queue, building up and then emitting complete
            event messages.
            """
            message_lines = []
            line_bytes = b""

            def emit_message(lines: List[str]):
                message_dict = {}
                for line in lines:
                    key_raw, value_raw = line.split(":", 1)
                    key = key_raw.strip()
                    value = value_raw.strip()
                    if key == "data":
                        message_dict["data"] = json.loads(value)
                    else:
                        message_dict[key] = value

                message = SseMessage(**message_dict)
                self.on_message(message)

            while True:
                new_bytes: bytes = await queue.get()
                line_bytes += new_bytes

                try:
                    decoded_line = line_bytes.decode("utf-8")
                except UnicodeError:
                    continue

                if decoded_line.endswith("\n"):
                    # We have a complete line
                    line_bytes = b""
                    stripped_line = decoded_line.rstrip("\n")
                    if stripped_line == "":
                        # Blank line - message is complete
                        emit_message(message_lines)
                        message_lines = []
                    else:
                        message_lines.append(stripped_line)

        loop = asyncio.get_event_loop()
        self._connection_task = loop.create_task(connection())
        self._message_emitter_task = loop.create_task(message_emitter())

        while not opened and not errored:
            print("waiting")
            await asyncio.sleep(1)

    async def close(self):
        self._connection_task.cancel()
        while not self._connection_task.cancelled():
            await asyncio.sleep(0)
        self._message_emitter_task.cancel()
        while not self._message_emitter_task.cancelled():
            await asyncio.sleep(0)
