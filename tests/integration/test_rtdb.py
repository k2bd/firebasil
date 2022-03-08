import asyncio
from datetime import timedelta

import pytest

from firebasil.exceptions import RtdbEventStreamException
from firebasil.rtdb import EventType, Rtdb, RtdbEvent, RtdbNode, SizeLimit


def example_filter_data():
    return {
        "aaa": {
            "height": 123,
            "weight": 999,
            "stats": {
                "wis": 10,
                "int": 11,
            },
        },
        "bbb": {
            "height": 234,
            "weight": 888,
            "stats": {
                "wis": 12,
                "int": 13,
            },
        },
        "ccc": {
            "height": 345,
            "weight": 777,
            "stats": {
                "wis": 9,
                "int": 10,
            },
        },
    }


@pytest.mark.asyncio
async def test_set_and_get_rtdb_root(rtdb_root: RtdbNode):
    """
    Can get and set data at the root level
    """
    data = {"a": "b", "c": "d"}
    set_data = await rtdb_root.set(data=data)
    assert set_data == data, set_data

    got_data = await rtdb_root.get()
    assert got_data == data, got_data

    got_subdata = await rtdb_root.child("a").get()
    assert got_subdata == "b", got_subdata


@pytest.mark.asyncio
async def test_order_by_key(rtdb_root: RtdbNode):
    """
    order_by_key, and limit_to_last
    """
    node = rtdb_root / "abcd"
    await node.set(example_filter_data())

    result = await node.order_by_key().limit_to_last(2).get()
    assert result == {
        "bbb": {
            "height": 234,
            "weight": 888,
            "stats": {
                "wis": 12,
                "int": 13,
            },
        },
        "ccc": {
            "height": 345,
            "weight": 777,
            "stats": {
                "wis": 9,
                "int": 10,
            },
        },
    }


@pytest.mark.asyncio
async def test_order_by_key_docs_example(rtdb_root: RtdbNode):
    """
    An example for the docs
    """
    # Set the database state from the root node
    await rtdb_root.set({"scores": {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}})

    # Build a child node that references the 'scores' path
    child_node = rtdb_root / "scores"

    # Get the value of the further 'c' child
    c_value = await (child_node / "c").get()
    assert c_value == 3

    # Query for the last two entries at that location, ordered by key
    query_value = await child_node.order_by_key().limit_to_last(2).get()
    assert query_value == {"d": 2, "e": 1}


@pytest.mark.xfail  # See k2bd/firebasil#6
@pytest.mark.asyncio
async def test_order_by_value(rtdb_root: RtdbNode):
    """
    order_by_value, and limit_to_first
    """
    node = rtdb_root / "scores"
    await node.set(
        {
            "a": 11,
            "b": 7,
            "c": 10,
            "d": 9,
            "e": 8,
            "f": 6,
        }
    )

    result = await node.order_by_value().limit_to_first(2).get()
    assert result == {
        "b": 7,
        "f": 6,
    }


@pytest.mark.xfail  # See k2bd/firebasil#6
@pytest.mark.asyncio
async def test_order_by_child(rtdb_root: RtdbNode):
    """
    Order by some child
    """
    node = rtdb_root / "abcd"
    await node.set(example_filter_data())

    result = await node.order_by("stats/int").limit_to_first(1).get()
    assert result == {
        "ccc": {
            "height": 345,
            "weight": 777,
            "stats": {
                "wis": 9,
                "int": 10,
            },
        },
    }


@pytest.mark.asyncio
async def test_order_by_priority(rtdb_root: RtdbNode):
    """
    order_by_priority
    """
    node = rtdb_root / "priotest"
    await node.set(
        {
            "a": {
                "name": "AAA",
                ".priority": 1.0,
            },
            "b": {
                "name": "BBB",
                ".priority": 1.5,
            },
            "c": {
                "name": "CCC",
                ".priority": 0.5,
            },
        }
    )

    result = await node.order_by_priority().limit_to_last(1).get()
    assert result == {"b": {"name": "BBB"}}


@pytest.mark.asyncio
async def test_start_at_and_end_at(rtdb_root: RtdbNode):
    """
    Start and end at
    """
    node = rtdb_root / "startEnd"
    await node.set(
        {
            "a": 12,
            "b": 44,
            "c": 13,
            "d": 0,
            "e": 50,
        }
    )

    result = await node.order_by_key().start_at("b").end_at("d").get()
    assert result == {
        "b": 44,
        "c": 13,
        "d": 0,
    }


@pytest.mark.asyncio
async def test_equal_to(rtdb_root: RtdbNode):
    """
    Search equal to
    """
    node = rtdb_root / "startEnd"
    await node.set(
        {
            "a": 12,
            "b": 44,
            "c": 13,
            "d": 0,
            "e": 50,
        }
    )

    result = await node.order_by_key().equal_to("d").get()
    assert result == {"d": 0}


@pytest.mark.asyncio
async def test_shallow_get(rtdb_root: RtdbNode):
    """
    Shallow get
    """
    node = rtdb_root / "shallowTest"
    await node.set(example_filter_data())

    result = await node.shallow().get()
    assert result == {
        "aaa": True,
        "bbb": True,
        "ccc": True,
    }


@pytest.mark.asyncio
async def test_order_by_priority_with_export_format(rtdb_root: RtdbNode):
    """
    order_by_priority with export format
    """
    node = rtdb_root / "priotest"
    await node.set(
        {
            "a": {
                "name": "AAA",
                ".priority": 1.0,
            },
            "b": {
                "name": "BBB",
                ".priority": 1.5,
            },
            "c": {
                "name": "CCC",
                ".priority": 0.5,
            },
        }
    )

    result = await node.order_by_priority().limit_to_last(1).export_format().get()
    assert result == {
        "b": {
            "name": "BBB",
            ".priority": 1.5,
        },
    }


@pytest.mark.parametrize(
    "timeout", [timedelta(seconds=1), timedelta(minutes=3), timedelta(seconds=1.1)]
)
@pytest.mark.asyncio()
async def test_timeouts(rtdb_root: RtdbNode, timeout: timedelta):
    """
    Timeouts don't fail
    """
    node = rtdb_root / "timeoutWriteLimit"
    await node.set(example_filter_data())
    result = await node.timeout(timeout).get()
    assert result == example_filter_data()


@pytest.mark.parametrize("write_limit", [e for e in SizeLimit])
@pytest.mark.asyncio()
async def test_write_limits(rtdb_root: RtdbNode, write_limit: SizeLimit):
    """
    Write limits don't fail
    """
    node = rtdb_root / "timeoutWriteLimit"
    await node.write_size_limit(write_limit).set(example_filter_data())
    result = await node.get()
    assert result == example_filter_data()


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

    messages = []

    async with observe_node.events() as events:
        await asyncio.sleep(1)
        await write_node.set(initial_state)
        await write_node.update({"a/a1": "new1", "a/a3": "new3", "b/b1": None})
        await (write_node / "a").delete()
        await asyncio.sleep(1)

        while not events.empty():
            msg = await events.get()
            messages.append(msg)

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
        ),
        RtdbEvent(
            event=EventType.patch,
            path="/bbb",
            data={"a/a1": "new1", "a/a3": "new3", "b/b1": None},
        ),
        RtdbEvent(
            event=EventType.put,
            path="/bbb/a",
            data=None,
        ),
    ]

    if len(messages) == 3:
        assert messages == expected_messages
    elif len(messages) == 4:
        spurious_event = RtdbEvent(
            event=EventType.put,
            path="/",
            data=None,
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
        with pytest.raises(RtdbEventStreamException):
            async with bogus_root.events():
                pass
