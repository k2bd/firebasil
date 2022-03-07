import contextlib
import os


@contextlib.contextmanager
def temp_env(**env):
    old_env = dict(os.environ)
    os.environ.update(env)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)
