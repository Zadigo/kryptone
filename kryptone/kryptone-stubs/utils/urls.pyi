import pathlib
import re
from collections import defaultdict
from functools import lru_cache
from string import Template
from typing import (Any, DefaultDict, Generator, List, Literal, Tuple, Union,
                    override)
from urllib.parse import ParseResult

import pandas

from kryptone.utils.urls import URL


@lru_cache(maxsize=100)
def load_image_extensions() -> list[str]: ...


class URL:
    raw_url: str = ...
    domain: str = ...
    url_object: ParseResult = ...

    def __init__(
        self,
        url: Union[URL, ParseResult, str],
        *,
        domain: str = ...
    ): ...

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __eq__(self, obj: URL) -> bool: ...
    def __add__(self, obj: str) -> URL: ...
    def __contains__(self, obj: Union[URL, str]) -> bool: ...
    def __hash__(self) -> int: ...
    def __len__(self) -> int: ...

    @property
    def is_path(self) -> bool: ...
    @property
    def is_valid(self) -> bool: ...
    @property
    def has_fragment(self) -> bool: ...
    @property
    def has_queries(self) -> bool: ...
    @property
    def has_path(self) -> bool: ...
    @property
    def is_image(self) -> bool: ...
    @property
    def is_file(self) -> bool: ...
    @property
    def as_path(self) -> pathlib.Path: ...
    @property
    def get_extension(self) -> Union[str, None]: ...
    @property
    def url_stem(self) -> str: ...
    @property
    def is_secured(self) -> bool: ...
    @property
    def query(self) -> dict[str, Any]: ...
    @classmethod
    def create(cls, url: str) -> URL: ...

    def is_same_domain(self, url: Union[str, URL]) -> bool: ...
    def get_status(self) -> Tuple[bool, int]: ...
    def compare(self, url_to_compare: Union[URL, str]) -> bool: ...
    def capture(self, regex: str) -> Union[re.Match, bool]: ...
    def test_url(self, regex: str) -> bool: ...
    def test_path(self, regex: str) -> bool: ...
    def decompose_path(self, exclude: List[str] = ...) -> List[str]: ...
    def remove_fragment(self) -> URL: ...


class BaseURLTestsMixin:
    blacklist: set = ...
    blacklist_distribution: DefaultDict[list] = ...
    error_message: str = ...

    def __call__(self, url: str) -> bool: ...

    def convert_url(self, url: Union[URL, str]) -> URL: ...


class URLIgnoreTest(BaseURLTestsMixin):
    name: str = ...
    paths: set[str] = ...

    def __init__(
        self,
        name: str,
        *,
        paths: List[str] = ...
    ): ...

    def __repr__(self) -> None: ...

    @override
    def __call__(self, url: str) -> bool: ...


class URLIgnoreRegexTest(BaseURLTestsMixin):
    name: str = ...
    regex: re.Pattern = ...

    def __init__(self, name: str, regex: str) -> str: ...

    @override
    def __call__(self, url: str) -> bool: ...


class BaseURLGenerator:
    def __repr__(self) -> str: ...
    def __iter__(self) -> Generator[str]: ...
    def __aiter__(self) -> Generator[str, None, None]: ...
    def __len__(self) -> int: ...

    def resolve_generator(self) -> Generator[str, None, None]: ...


class URLQueryGenerator(BaseURLGenerator):
    def __init__(
        self,
        url: str,
        *,
        param: str = ...,
        param_values: list[str] = ...,
        query: dict[str, str] = ...
    ) -> None: ...


class URLPathGenerator(BaseURLGenerator):
    base_template_url: Template = ...
    urls: List = ...
    params: dict[str, str] = ...,
    k: int = ...,
    start: int = ...

    def __init__(
        self,
        template: str,
        params: dict[str, str] = ...,
        k: int = ...,
        start: int = ...
    ) -> None: ...


class URLPaginationGenerator(BaseURLGenerator):
    urls: list = ...
    final_urls: list = ...
    url: URL = ...
    param_name: Literal['page'] = ...
    k: Literal[10] = ...

    def __init__(
        self,
        url: Union[str, URL],
        query: Literal['page'] = ...,
        k: Literal[10] = ...
    ) -> None: ...


class MultipleURLManager:
    _urls_to_visit: set[str] = ...
    _visited_urls: set[str] = ...
    _seen_urls: set[str] = ...
    _grouped_by_page = defaultdict
    _current_url: URL = ...
    sort_urls: bool = ...
    dataframe: pandas.DataFrame = ...

    def __init__(self, start_urls=[], sort_urls=False,
                 convert_objects=False) -> None: ...

    def __repr__(self) -> str: ...
    def __iter__(self) -> Generator[str, None, None]: ...
    def __contains__(self, url) -> bool: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index) -> URL: ...

    @property
    def empty(self) -> bool: ...
    @lru_cache(maxsize=100)
    def all_urls(self) -> set[str]: ...
    @property
    def urls_to_visit(self) -> Generator[URL, None, None]: ...
    @property
    def visited_urls(self) -> Generator[URL, None, None]: ...
    @property
    def urls_to_visit_count(self) -> int: ...
    @property
    def visited_urls_count(self) -> int: ...
    @property
    def total_urls_count(self) -> int: ...
    @property
    def completion_rate(self) -> float: ...
    @property
    def next_url(self) -> str: ...
    @property
    def grouped_by_page(self) -> dict: ...

    def pre_save(self, urls) -> list: ...
    def backup(self) -> dict[str, Any]: ...

    def append_multiple(
        self,
        urls: Union[list[str], set[str]]
    ) -> tuple[set[str], set[str]]: ...

    def append(self, url) -> None: ...
    def appendleft(self, url) -> None: ...
    def clear(self) -> None: ...
    def reverse(self) -> None: ...
    def update(self, urls, current_url=...) -> None: ...
    def get(self) -> URL: ...


class LoadStartUrls(BaseURLGenerator):
    filename: str = ...
    is_json: bool = ...

    def __init__(
        self,
        *,
        filename: str = ...,
        is_json: bool = ...
    ) -> None: ...
