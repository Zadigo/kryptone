from ctypes import Union
from typing import List, Tuple
from typing import OrderedDict
from typing import Callable
from typing import Self

from kryptone.base import SiteCrawler
from kryptone.utils.urls import URL

class Route:
    path: str = ...
    regex: str = ...
    name: str = ...
    function_name: str = ...
    matched_urls: list = ...

    def __init__(self: Self) -> None: ...
    def __repr__(self: Self) -> str: ...

    def __call__(
        self: Self,
        function_name: str,
        *,
        path: str = ...,
        regex: str = ...,
        name: str = ...
    ) -> Tuple[Self, Callable[[str, SiteCrawler], bool]]: ...


route: Route = ...


class Router:
    routes: OrderedDict[str, Callable[[str, SiteCrawler], bool]] = OrderedDict()

    def __init__(self: Self, routes: List[Route]) -> None: ...
    def __repr__(self: Self) -> str: ...

    @property
    def has_routes(self) -> bool: ...
    def resolve(self, current_url: Union[str, URL]) -> None: ...
