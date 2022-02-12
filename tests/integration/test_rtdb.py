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
