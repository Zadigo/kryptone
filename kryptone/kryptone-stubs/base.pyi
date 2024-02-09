import datetime
import time
from typing import (Any, Coroutine, DefaultDict, Iterator, List, Literal,
                    NamedTuple, Tuple, Union)
from urllib.parse import ParseResult
from urllib.robotparser import RobotFileParser

import pandas
from selenium.webdriver import Chrome, Edge
from selenium.webdriver.remote.webelement import WebElement

from kryptone.routing import Router
from kryptone.utils.file_readers import LoadStartUrls
from kryptone.utils.iterators import AsyncIterator
from kryptone.utils.urls import URL, URLIgnoreRegexTest, URLIgnoreTest

WEBDRIVER_ENVIRONMENT_PATH: str = 'KRYPTONE_WEBDRIVER'


def get_selenium_browser_instance(
    browser_name: str = ...,
    headless: bool = ...,
    load_images: bool = ...,
    load_js: bool = ...
) -> Union[Edge, Chrome]: ...


class PerformanceAudit(NamedTuple):
    days: int
    duration: int


class URLsAudit(NamedTuple):
    count_urls_to_visit: int
    count_visited_urls: int
    completion_percentage: float
    total_urls: int


class CrawlerOptions:
    spider: SiteCrawler = ...
    spider_name: str = ...
    verbose_name: str = ...
    initial_spider_meta: type = ...
    domains: list[str] = ...
    audit_page: bool = ...
    url_ignore_tests: Union[URLIgnoreRegexTest, URLIgnoreTest] = ...
    debug_mode: bool = ...
    site_language: Literal['en'] = ...
    default_scroll_step: Literal[80] = ...
    router: Router = ...
    crawl: bool = ...
    start_urls: Union[LoadStartUrls, list[str]]
    restrict_search_to: list[str] = ...
    ignore_queries: bool = ...
    ignore_images: bool = ...
    url_gather_ignore_tests: list = ...

    def __repr__(self) -> str: ...
    def add_meta_options(self, options: tuple) -> None: ...
    def prepare(self) -> None: ...


class Crawler(type):
    def __new__(cls: type, name: str, bases: tuple, attrs: dict) -> type: ...
    def prepare(cls: type) -> None: ...


class BaseCrawler(metaclass=Crawler):
    urls_to_visit: set[str] = ...
    visited_urls: set[str] = ...
    visited_pages_count: int = ...
    list_of_seen_urls: set[str] = ...
    browser_name: str = ...
    timezone: str = Literal['UTC']
    default_scroll_step:  int = Literal[80]
    _start_url_object: URL = ...
    url_distribution: DefaultDict = ...
    driver: Union[Edge, Chrome] = ...

    class Meta:
        ...

    def __init__(self, browser_name: str = ...): ...
    def __repr__(self) -> str: ...
    @property
    def get_page_link_elements(self) -> List[str]: ...
    @property
    def get_title_element(self) -> WebElement: ...
    @property
    def get_origin(self) -> str: ...
    def _backup_urls(self) -> None: ...
    def _get_robot_txt_parser(self) -> RobotFileParser: ...
    def urljoin(self, path: str) -> str: ...
    def url_structural_check(self, url: str) -> URL: ...

    def url_filters(
        self,
        valid_urls: list[str]
    ) -> set[str]: ...

    def url_rule_test_filter(
        self,
        valid_urls: list[str]
    ) -> set[str]: ...

    def add_urls(self, *urls_or_paths: str) -> None: ...
    def get_page_urls(self, current_url: URL, refresh: bool = ...) -> None: ...

    def click_consent_button(
        self,
        element_id: str = ...,
        element_class: str = ...,
        before_click_wait_time: int = ...,
        wait_time: int = ...
    ) -> None: ...

    def calculate_performance(self) -> Tuple[PerformanceAudit, URLsAudit]: ...
    def post_navigation_actions(self, current_url: URL, **kwargs) -> None: ...
    def before_next_page_actions(self, current_url: URL, **kwargs) -> None: ...

    def current_page_actions(
        self,
        current_url: URL,
        current_json_object: pandas.DataFrame = ...,
        **kwargs
    ) -> None: ...
    def create_dump(self) -> None: ...


class SiteCrawler(BaseCrawler):
    _start_date: datetime.datetime = ...
    _start_time: time.time
    _end_time: time.time
    _meta: CrawlerOptions = ...
    start_url: str = ...
    performance_audit: PerformanceAudit = ...
    urls_audit: URLsAudit = ...
    statistics: dict[str, int] = ...
    # cached_json_items: pandas.DataFrame = ...
    # enrichment_mode: bool = ...

    def __init__(self, browser_name: str = ...) -> None: ...
    def __del__(self) -> None: ...
    @classmethod
    def create(cls, **params: Any) -> SiteCrawler: ...
    def before_start(self, start_urls: list[str], **kwargs) -> None: ...
    def resume(self, **kwargs): ...
    def start_from_sitemap_xml(self, url: str, **kwargs): ...
    def start_from_html_sitemap(self, url: str, **kwargs): ...
    # def start_from_json(self, windows: int = ..., **kwargs) -> None: ...

    def start(
        self,
        start_urls: List[str] = ...,
        **kwargs
    ) -> None: ...

    def boost_start(
        self,
        start_urls: list[str],
        *,
        windows: int = ...,
        **kwargs
    ) -> None: ...


class JSONCrawler:
    base_url: str = ...
    receveived_data: List[list, dict[str, Any]] = ...
    date_sorted_data: DefaultDict[list] = ...
    iterator: AsyncIterator = ...
    chunks: int = Literal[10]
    request_sent: int = Literal[0]
    max_pages: int = Literal[0]
    current_page_key: str = ...
    current_page: int = Literal[1]
    max_pages_key: int = ...
    paginate_data: bool = ...
    pagination: int = Literal[0]
    _url: URL = ...

    def __init__(self, chunks: int = ...): ...

    @property
    def data(self) -> List[Iterator[list, dict]]: ...

    async def create_dump(self) -> Coroutine[None, None, None]: ...

    async def clean(
        self,
        data: Union[list, dict[str, Any]]
    ) -> Coroutine[None, None, pandas.DataFrame]: ...

    async def start(
        self, interval: int = ...
    ) -> Coroutine[None, None, None]: ...
