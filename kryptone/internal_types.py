import pathlib
import time
import datetime
from typing import TYPE_CHECKING, Any, Protocol, Optional, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from kryptone.base import SiteCrawler


T = TypeVar('T')

_SiteCrawler = TypeVar('_SiteCrawler', bound='SiteCrawler')


@runtime_checkable
class PerformanceAuditProtocol(Protocol):
    iteration_count: int
    start_date: datetime.datetime
    end_date: datetime.datetime
    timezone: str | Any
    error_count: int
    duration: int
    count_urls_to_visit: int
    count_visited_urls: int
    def calculate_duration(self) -> None: ...
    def add_error_count(self) -> None: ...
    def add_iteration_count(self) -> None: ...
    def load_statistics(self, data: dict[str, Any]) -> None: ...
    def json(self) -> dict: ...


@runtime_checkable
class FileProtocol(Protocol):
    path: pathlib.Path
    def __eq__(self, value: Any) -> bool: ...
    @property
    def is_json(self) -> bool: ...
    @property
    def is_csv(self) -> bool: ...
    @property
    def is_image(self) -> bool: ...

    async def read(self) -> dict[str,
                                 Any] | list[dict[str, Any]] | list[list[Any]]: ...
