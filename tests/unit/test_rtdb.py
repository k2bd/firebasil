from typing import List
from unittest import mock

import pytest

from firebasil.rtdb import RtdbNode

TEST_CHILD_PATHS_AND_EXPECTED = [
    [
        [
            "aaa",
        ],
        "aaa",
    ],
    [["aaa", "bbb"], "aaa/bbb"],
    [["aaa", "bbb", "ccc"], "aaa/bbb/ccc"],
]


@pytest.mark.parametrize(
    ["paths", "expected_path"],
    TEST_CHILD_PATHS_AND_EXPECTED,
)
def test_child_single(paths: List[str], expected_path: str):
    node = RtdbNode(_rtdb=mock.Mock())

    assert node.child(*paths).path == expected_path


@pytest.mark.parametrize(
    ["paths", "expected_path"],
    TEST_CHILD_PATHS_AND_EXPECTED,
)
def test_child_multi(paths: List[str], expected_path: str):
    node = RtdbNode(_rtdb=mock.Mock())

    for path in paths:
        node = node.child(path)

    assert node.path == expected_path
