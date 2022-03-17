# firebasil

[![CI](https://github.com/k2bd/firebasil/actions/workflows/ci.yml/badge.svg)](https://github.com/k2bd/firebasil/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/k2bd/firebasil/branch/main/graph/badge.svg?token=0X48PIN0MC)](https://codecov.io/gh/k2bd/firebasil)
[![PyPI](https://img.shields.io/pypi/v/firebasil)](https://pypi.org/project/firebasil/)
[![Documentation Status](https://readthedocs.org/projects/firebasil/badge/?version=latest)](https://firebasil.readthedocs.io/en/latest/?badge=latest)

A modern async Firebase client.

# Features

## Auth

[![Auth Baseline](https://img.shields.io/github/milestones/progress/k2bd/firebasil/1)](https://github.com/k2bd/firebasil/milestone/1)
[![Auth High level](https://img.shields.io/github/milestones/progress/k2bd/firebasil/6)](https://github.com/k2bd/firebasil/milestone/6)

The `AuthClient` async context manager provides access to auth routines.
Every method returns a typed object with the information provided by the Firebase auth REST API.

```python
from firebasil.auth import AuthClient


async with AuthClient(api_key=...) as auth_client:
    # Sign up a new user
    signed_up = await auth_client.sign_up("kevin@k2bd.dev", "password1")

    # Sign in as a user
    signed_in = await auth_client.sign_in_with_password(
        email="kevin@k2bd.dev",
        password="password1",
    )

    updated = await auth_client.update_profile(
        signed_in.id_token,
        display_name="Kevin Duff",
    )
```

The `AuthClient` class will use production GCP endpoints and routes for auth by default, unless the `FIREBASE_AUTH_EMULATOR_HOST` environment variable is set, in which case the defaults change to the emulator. This can be overridden in both cases by passing in `identity_toolkit_url`, `secure_token_url`, and `use_emulator_routes` explicitly.

## Realtime Database (RTDB)

[![RTDB Baseline](https://img.shields.io/github/milestones/progress/k2bd/firebasil/2)](https://github.com/k2bd/firebasil/milestone/2)
[![RTDB High level](https://img.shields.io/github/milestones/progress/k2bd/firebasil/5)](https://github.com/k2bd/firebasil/milestone/5)

The `Rtdb` async context manager yields the root node of the database.

```python
from firebasil.rtdb import Rtdb


async with Rtdb(database_url=...) as root_node:

    # Set the database state from the root node
    await rtdb_root.set({"scores": {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}})

    # Build a child node that references the 'scores' path
    child_node: RtdbNode = rtdb_root / "scores"

    # Get the value of the further 'c' child
    c_value = await (child_node / "c").get()
    assert c_value == 3

    # Query for the last two entries at that location, ordered by key
    query_value = await child_node.order_by_key().limit_to_last(2).get()
    assert query_value == {"d": 2, "e": 1}

    # Watch a node for live changes
    async with child_node.events() as event_queue:
        event: RtdbEvent = await event_queue.get()
        ...
        # Somewhere, 'b' gets set to 7
        # RtdbEvent(event=EventType.put, path='/b', data=7)
```

Either a user ID token, or a machine credential access token, can be provided `Rtdb` through the `id_token` or `access_token` arguments, which will be used to pass the database's auth.

A local emulator URL may be passed to `Rtdb` to test against the Firebase Emulator Suite.

## Firestore Database

[![Firestore Baseline](https://img.shields.io/github/milestones/progress/k2bd/firebasil/3)](https://github.com/k2bd/firebasil/milestone/3)

Still in planning!

## Storage

[![Storage Baseline](https://img.shields.io/github/milestones/progress/k2bd/firebasil/4)](https://github.com/k2bd/firebasil/milestone/4)

Still in planning!

# Developing on this Project

## Installation

Install [Poetry](https://python-poetry.org/) and `poetry install` the project

Install the [Firebase CLI](https://firebase.google.com/docs/cli). Make sure the emulators are installed and configured with `firebase init emulators`.

### Useful Commands

Note: if Poetry is managing a virtual environment for you, you may need to use `poetry run poe` instead of `poe`

- `poe autoformat` - Autoformat code
- `poe lint` - Linting
- `poe test` - Run tests
- `poe docs` - Build docs

### Release

Release a new version by manually running the release action on GitHub with a 'major', 'minor', or 'patch' version bump selected.
This will create an push a new semver tag of the format `v1.2.3`.

Pushing this tag will trigger an action to release a new version of your library to PyPI.

Optionally create a release from this new tag to let users know what changed.
