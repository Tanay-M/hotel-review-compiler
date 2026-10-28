"""Thread/task-local compiler configuration; original experiments stay usable."""
from contextlib import contextmanager
from contextvars import ContextVar

_PROFILE = ContextVar('hotel_compiler_profile', default='original')
PROFILES = ('original', 'expanded')


def current_profile():
    return _PROFILE.get()


@contextmanager
def compiler_profile(name):
    if name not in PROFILES:
        raise ValueError('Compiler profile must be original or expanded.')
    token = _PROFILE.set(name)
    try:
        yield
    finally:
        _PROFILE.reset(token)
