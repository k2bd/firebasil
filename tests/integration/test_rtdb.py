import asyncio
from datetime import datetime, timezone

import pytest
from freezegun import freeze_time

from firebasil.exceptions import RtdbListenerConnectionException
from firebasil.rtdb import EventType, Rtdb, RtdbEvent, RtdbNode

from .helpers import rtdb_events_list


@pytest.mark.asyncio
async def test_set_and_get_rtdb_root(rtdb_root: RtdbNode):
    """
    Can get and set data at the root level
    """
    data = {
        "a": "b",
        "c": "d",
    }
    set_data = await rtdb_root.set(data=data)
    assert set_data == data, set_data

    got_data = await rtdb_root.get()
    assert got_data == data, got_data

    got_subdata = await rtdb_root.child("a").get()
    assert got_subdata == "b", got_subdata


@pytest.mark.asyncio
async def test_set_and_get_rtdb_child(rtdb_root: RtdbNode):
    """
    Can get and set data at a child level
    """
    data = [{"a": "b"}, {"a": "c"}, {"a": "d"}]
    child = rtdb_root.child("aaa", "bbb")

    set_data = await child.set(data=data)
    assert set_data == data, set_data

    got_data = await child.get()
    assert got_data == data, got_data


@pytest.mark.asyncio
async def test_add_to_list(rtdb_root: RtdbNode):
    """
    Can append to list data
    """
    child = rtdb_root / "logs"

    new_key_1 = await child.push({"message": "Hello"})

    assert await child.get() == {
        new_key_1: {"message": "Hello"},
    }

    new_key_2 = await child.push({"message": "World"})

    assert await child.get() == {
        new_key_1: {"message": "Hello"},
        new_key_2: {"message": "World"},
    }

    assert await rtdb_root.get() == {
        "logs": {
            new_key_1: {"message": "Hello"},
            new_key_2: {"message": "World"},
        }
    }


@pytest.mark.asyncio
async def test_update(rtdb_root: RtdbNode):
    """
    Can update multiple locations in the DB
    """
    initial_state = {
        "a": {
            "a1": "1",
            "a2": "2",
        },
        "b": {
            "b1": {
                "b11": "1",
                "b12": "2",
            },
            "b2": "2",
        },
    }
    await rtdb_root.set(initial_state)

    await rtdb_root.update({"a/a1": "new1", "a/a3": "new3", "b/b1": None})

    assert await rtdb_root.get() == {
        "a": {
            "a1": "new1",
            "a2": "2",
            "a3": "new3",
        },
        "b": {
            "b2": "2",
        },
    }


@pytest.mark.asyncio
async def test_listener(rtdb_root: RtdbNode):
    """
    Can update multiple locations in the DB
    """
    initial_state = {
        "a": {
            "a1": "1",
            "a2": "2",
        },
        "b": {
            "b1": {
                "b11": "1",
                "b12": "2",
            },
            "b2": "2",
        },
    }
    observe_node = rtdb_root / "aaa"
    write_node = observe_node / "bbb"

    frozen_time = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    with freeze_time(frozen_time):
        async with rtdb_events_list(observe_node) as messages:
            print("AAA")
            await write_node.set(initial_state)

            print("BBB")
            await write_node.update({"a/a1": "new1", "a/a3": "new3", "b/b1": None})
            print("CCC")

            await (write_node / "a").delete()
            print("DDD")

            # await asyncio.sleep(3)
            # print("EEE")

    # N.B. seems to always grab the cleanup from the previous test...
    assert len(messages) in [3, 4]
    expected_messages = [
        RtdbEvent(
            event=EventType.put,
            path="/bbb",
            data={
                "a": {"a1": "1", "a2": "2"},
                "b": {"b1": {"b11": "1", "b12": "2"}, "b2": "2"},
            },
            time_received=frozen_time,
        ),
        RtdbEvent(
            event=EventType.patch,
            path="/bbb",
            data={"a/a1": "new1", "a/a3": "new3", "b/b1": None},
            time_received=frozen_time,
        ),
        RtdbEvent(
            event=EventType.put,
            path="/bbb/a",
            data=None,
            time_received=frozen_time,
        ),
    ]

    if len(messages) == 3:
        assert messages == expected_messages
    elif len(messages) == 4:
        spurious_event = RtdbEvent(
            event=EventType.put,
            path="/",
            data=None,
            time_received=frozen_time,
        )
        assert messages == [spurious_event] + expected_messages
    else:
        pytest.fail("Unexpected messages length")


@pytest.mark.asyncio
async def test_listener_cant_connect():
    """
    Raise correct exception if we can't connect
    """

    def on_event(e):
        pass

    async with Rtdb(database_url="http://nothing") as bogus_root:
        with pytest.raises(RtdbListenerConnectionException):
            async with bogus_root.listen(on_event=on_event):
                pass
