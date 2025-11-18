import functools
from typing import Callable

from kryptone import logger


def deprecated(func: Callable) -> Callable:
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""
    import functools
    import warnings

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        logger.warning(f"Call to deprecated function '{func.__name__}'")
        return func(*args, **kwargs)

    return new_func
