from typing import Any, Dict

import pytest

from firebasil.auth.auth import snakeify_dict_keys


@pytest.mark.parametrize(
    "raw, expected",
    [
        (  # Simple JSON dict
            {
                "aaa": "bbb",
                "camelCase": "camelCaseVal",
                "snake_case": "snake_case_val",
                "NumBer": 123,
            },
            {
                "aaa": "bbb",
                "camel_case": "camelCaseVal",
                "snake_case": "snake_case_val",
                "num_ber": 123,
            },
        ),
        (  # More complex JSON dict
            {
                "listOfScalar": ["aaa", "bbbCcc", 111],
                "object": {
                    "aaa": "bbb",
                    "camelCase": "camelCaseVal",
                    "snake_case": "snake_case_val",
                    "NumBer": 123,
                },
                "listOfObjects": [
                    {"fullName": "johnSmith"},
                    {"fullName": "saintNick"},
                    {"fullName": "kevin"},
                ],
                "deepObject": {
                    "listOfScalar": ["aaa", "bbbCcc", 111],
                    "object": {
                        "aaa": "bbb",
                        "camelCase": "camelCaseVal",
                        "snake_case": "snake_case_val",
                        "NumBer": 123,
                    },
                    "listOfObjects": [
                        {"fullName": "johnSmith"},
                        {"fullName": "saintNick"},
                        {"fullName": "kevin"},
                    ],
                },
            },
            {
                "list_of_scalar": ["aaa", "bbbCcc", 111],
                "object": {
                    "aaa": "bbb",
                    "camel_case": "camelCaseVal",
                    "snake_case": "snake_case_val",
                    "num_ber": 123,
                },
                "list_of_objects": [
                    {"full_name": "johnSmith"},
                    {"full_name": "saintNick"},
                    {"full_name": "kevin"},
                ],
                "deep_object": {
                    "list_of_scalar": ["aaa", "bbbCcc", 111],
                    "object": {
                        "aaa": "bbb",
                        "camel_case": "camelCaseVal",
                        "snake_case": "snake_case_val",
                        "num_ber": 123,
                    },
                    "list_of_objects": [
                        {"full_name": "johnSmith"},
                        {"full_name": "saintNick"},
                        {"full_name": "kevin"},
                    ],
                },
            },
        ),
    ],
)
def test_snakeify_dict_keys(raw: Dict[str, Any], expected: Dict[str, Any]):
    assert snakeify_dict_keys(raw) == expected
