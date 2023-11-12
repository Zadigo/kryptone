from collections import OrderedDict
from functools import lru_cache
from types import ModuleType
from typing import List, Literal, Union

from kryptone.base import JSONCrawler, SiteCrawler
from kryptone.conf import Settings

SPIDERS_MODULE: str = Literal['spiders']

ENVIRONMENT_VARIABLE: str = Literal['KRYPTONE_SPIDER']


class SpiderConfig:
    name: str = name
    dotted_path: str = None
    registry: MasterRegistry = None
    spider_class: Union[SiteCrawler, JSONCrawler] = ...

    MODULE: ModuleType = ...
    paths: str = ...
    is_read: bool = ...

    def __init__(self, name: str, spiders_module: ModuleType) -> None: ...
    def __repr__(self) -> str: ...

    @classmethod
    def create(
        cls,
        name: str,
        module: ModuleType,
        dotted_path: str = ...
    ) -> SpiderConfig: ...

    def get_spider_instance(self) -> Union[SiteCrawler, JSONCrawler]: ...
    def check_ready(self) -> None: ...
    def run(self, **kwargs) -> None: ...
    def resume(self, **kwargs) -> None: ...


class MasterRegistry:
    is_ready: bool = ...
    spiders_ready: bool = ...
    spiders: OrderedDict[str, Union[SiteCrawler, JSONCrawler]] = ...
    project_name: str = ...
    absolute_path: str = ...
    middlewares: list[str] = ...
    has_running_spiders: bool = ...

    def __init__(self) -> None: ...

    @property
    def has_spiders(self) -> bool: ...

    @lru_cache(maxsize=1)
    def get_spiders(self) -> List[Union[SiteCrawler, JSONCrawler]]: ...

    def has_spider(self, name: str) -> bool: ...
    def check_spiders_ready(self) -> None: ...

    def pre_configure_project(
        self,
        dotted_path: str,
        settings: Settings
    ) -> None: ...

    def populate(self) -> None: ...

    def get_spider(
        self,
        spider_name: str
    ) -> Union[SiteCrawler, JSONCrawler]: ...


registry: MasterRegistry = ...