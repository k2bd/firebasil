from contextlib import asynccontextmanager

from firebasil.rtdb import RtdbEvent, RtdbNode


@asynccontextmanager
async def rtdb_events_list(node: RtdbNode):

    messages = []

    def handle_event(event: RtdbEvent):
        print(event)
        messages.append(event)

    async with node.listen(on_event=handle_event):
        yield messages
