import pytest

from firebasil.rtdb import RtdbNode


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
