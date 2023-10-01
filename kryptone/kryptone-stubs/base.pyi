import datetime
import time
from typing import List, Literal, NamedTuple, NoReturn, Tuple, Union
from urllib.parse import ParseResult

from selenium.webdriver import Chrome, Edge
from selenium.webdriver.remote.webelement import WebElement

from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.routing import Router
from kryptone.utils.file_readers import URLCache
from kryptone.utils.urls import URL, UrlPassesRegexTest, URLPassesTest

WEBDRIVER_ENVIRONMENT_PATH: str = 'KRYPTONE_WEBDRIVER'


def get_selenium_browser_instance(
    browser_name: str = ...
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
    url_passes_tests: Union[URLPassesTest, UrlPassesRegexTest] = ...
    debug_mode: bool = ...
    site_language: Literal['en'] = ...
    default_scroll_step: Literal[80] = ...
    gather_emails: bool = ...
    router: Router = ...

    def __repr__(self) -> str: ...
    def add_meta_options(self, options: tuple) -> None: ...
    def prepare(self) -> None: ...


class Crawler(type):
    def __new__(cls, name: str, bases: tuple, attrs: dict) -> type: ...
    def prepare(cls: type) -> None: ...


class BaseCrawler(metaclass=Crawler):
    urls_to_visit: set[str] = ...
    visited_urls: set[str] = ...
    list_of_seen_urls: set[str] = ...
    browser_name: str = ...
    debug_mode: bool = ...
    timezone: str = 'UTC'
    default_scroll_step:  int = 80

    class Meta:
        ...

    def __init__(self, browser_name: str = ...): ...
    def __repr__(self) -> str: ...
    @property
    def get_html_page_content(self) -> str: ...
    @property
    def get_page_link_elements(self) -> List[WebElement]: ...
    @property
    def name(self) -> str: ...
    @property
    def get_html_page_content(self) -> str: ...
    @property
    def get_page_link_elements(self) -> List[WebElement]: ...
    @property
    def get_title_element(self) -> WebElement: ...
    @property
    def completion_percentage(self) -> int: ...
    def _backup_urls(self) -> None: ...
    def urljoin(self, path: str) -> str: ...

    def create_filename(
        self,
        length: int = ...,
        extension: str = ...
    ) -> str: ...
    def build_headers(self, options: dict) -> None: ...
    def run_filters(self) -> Union[list, set]: ...
    def add_urls(self, *urls_or_paths) -> None: ...
    def get_page_urls(self): ...

    def scroll_window(
        self,
        wait_time: int = ...,
        increment: int = ...,
        stop_at: int = ...
    ) -> None: ...

    def click_consent_button(
        self,
        element_id: str = ...,
        element_class: str = ...,
        wait_time: int = ...
    ) -> None: ...

    def evaluate_xpath(self, path: str) -> None: ...

    def scroll_page_section(
        self,
        xpath: str = ...,
        css_selector: str = ...
    ): ...

    def calculate_performance(self) -> None: ...
    def calculate_completion_percentage(self) -> None: ...
    def get_current_date(self) -> datetime.datetime: ...
    def post_visit_actions(self, **kwargs): ...
    def run_actions(self, current_url: URL, **kwargs) -> None: ...
    def create_dump(self) -> None: ...


class SiteCrawler(SEOMixin, EmailMixin, BaseCrawler):
    start_url: str = ...
    start_xml_url: str = ...
    _start_url_object: ParseResult = ...
    _start_date: datetime.datetime = ...
    _start_time: time.time
    _meta: CrawlerOptions = ...
    driver: Union[Edge, Chrome] = ...
    performance_audit: PerformanceAudit = ...
    urls_audit: URLsAudit = ...
    statistics: dict = ...

    def __init__(self, browser_name: str = ...) -> None: ...
    def resume(self, **kwargs): ...
    def start_from_sitemap_xml(self, url: str, **kwargs): ...
    def start_from_html_sitemap(self, url: str, **kwargs): ...

    def start(
        self,
        start_urls: List[str] = ...,
        **kwargs
    ) -> None: ...
