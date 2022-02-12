# firebasil

[![CI](https://github.com/k2bd/firebasil/actions/workflows/ci.yml/badge.svg)](https://github.com/k2bd/firebasil/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/k2bd/firebasil/branch/main/graph/badge.svg?token=0X48PIN0MC)](https://codecov.io/gh/k2bd/firebasil)
[![PyPI](https://img.shields.io/pypi/v/firebasil)](https://pypi.org/project/firebasil/)

A modern async Firebase library.

Docs TBD

## Developing

Install [Poetry](https://python-poetry.org/) and `poetry install` the project

Install the [Firebase CLI](https://firebase.google.com/docs/cli). Make sure the emulators are installed and configured with `firebase init emulators`.

### Useful Commands

Note: if Poetry is managing a virtual environment for you, you may need to use `poetry run poe` instead of `poe`

- `poe autoformat` - Autoformat code
- `poe lint` - Linting
- `poe test` - Run Tests

### Release

Release a new version by manually running the release action on GitHub with a 'major', 'minor', or 'patch' version bump selected.
This will create an push a new semver tag of the format `v1.2.3`.

Pushing this tag will trigger an action to release a new version of your library to PyPI.

Optionally create a release from this new tag to let users know what changed.
