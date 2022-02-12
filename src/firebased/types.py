from typing import List, Mapping, Union

# N.B. unfortunately mypy's cyclic definition support is incomplete.
# However I'll still use a cyclic type for now so it's ready for when we can
# validate against it.

#: A JSON value
JSON = Union[  # type: ignore
    None,
    str,
    int,
    float,
    bool,
    List["JSON"],  # type: ignore
    Mapping[str, "JSON"],  # type: ignore
]
