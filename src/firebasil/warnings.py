import inspect
import warnings
from functools import wraps


class FirebasilExperimentalWarning(Warning):
    """
    A feature is experimental, and may not work as intended yet.
    """


def experimental(message: str):
    """
    Marks an experimental feature
    """

    def _experimental(func):
        @wraps(func)
        async def _inner_async(*args, **kwargs):
            warnings.warn(message, FirebasilExperimentalWarning)
            return await func(*args, **kwargs)

        @wraps(func)
        def _inner_normal(*args, **kwargs):
            warnings.warn(message, FirebasilExperimentalWarning)
            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return _inner_async
        else:
            return _inner_normal

    return _experimental
