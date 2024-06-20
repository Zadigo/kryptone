import threading
from functools import lru_cache
from typing import Any, Callable

NO_RECEIVERS: object


@lru_cache(maxsize=512)
def get_function_parameters(func, remove_first) -> list: ...


def get_callable_parameters(func) -> list: ...


def test_function_accept_kwargs(func) -> bool: ...


def make_id(item) -> int: ...


NONE_ID: int


class Signal:
    receivers: list = ...
    lock: threading.Lock = ...
    sender_receivers_cache: dict = ...
    _has_dead_receivers: bool = ...

    def __init__(self) -> None: ...

    def _remove_receiver(self) -> None: ...
    def _clear_dead_receivers(self) -> None: ...
    def _live_receivers(self, sender: Callable[..., Any]) -> list: ...

    def has_listeners(self, sender: Callable[..., Any] = ...) -> bool: ...

    def connect(
        self,
        receiver: Callable[..., None],
        sender: Callable[..., Any] = ...,
        weak: bool = ...,
        uid: int = ...
    ) -> None: ...

    def disconnect(
        self,
        receiver: Callable[..., None] = ...,
        sender: Callable[..., Any] = ...,
        uid: int = ...
    ) -> bool: ...

    def send(
        self,
        sender: Callable[..., Any], 
        **named
    ) -> list: ...
    
    def send_to_all(
        self, 
        sender: Callable[..., Any], 
        **named
    ) -> list[tuple]: ...


def function_to_receiver(
    signal: Callable[..., None],
    **kwargs
) -> Callable[[Callable[..., None]], None]: ...
