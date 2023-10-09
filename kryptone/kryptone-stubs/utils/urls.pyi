import pathlib
import re
from functools import lru_cache
from string import Template
from typing import Generator, List, Tuple, Union
from urllib.parse import ParseResult


class URL:
    raw_url: str = ...
    url_object: ParseResult = ...

    def __init__(self, url_string: str): ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __eq__(self, obj: URL) -> bool: ...
    def __add__(self, obj: URL) -> ParseResult: ...
    def __contains__(self, obj: URL) -> bool: ...
    def __hash__(self) -> int: ...
    def __len__(self) -> int: ...

    @property
    def is_path(self) -> bool: ...
    @property
    def is_valid(self) -> bool: ...
    @property
    def has_fragment(self) -> bool: ...
    @property
    def is_file(self) -> bool: ...
    @property
    def as_path(self) -> pathlib.Path: ...
    @property
    def get_extension(self) -> Union[str, None]: ...
    @property
    def url_stem(self) -> str: ...
    @classmethod
    def create(cls, url) -> URL: ...

    def is_same_domain(self, url: Union[str, URL]) -> bool: ...
    def get_status(self) -> Tuple[bool, int]: ...
    def compare(self, url_to_compare: Union[URL, str]) -> bool: ...
    def capture(self, regex: str) -> Union[re.Match, bool]: ...
    def test_url(self, path: str) -> bool: ...
    def test_path(self, regex: str) -> bool: ...
    def decompose_path(self, exclude: List = ...) -> List: ...
    def paginate(self, regex_path: str = ..., param: str = ...) -> str: ...


class CompareUrls:
    current_url: URL = ...
    url_to_test: URL = ...
    test_result: bool = ...

    def __init__(self, current_url: str, url_to_test: str) -> None: ...
    def __repr__(self) -> str: ...
    def __bool__(self) -> bool: ...


class BaseURLTestsMixin:
    blacklist: list = ...

    def __call__(self, url: str) -> bool: ...

    def convert_url(self, url: str) -> URL: ...


class URLIgnoreTest(BaseURLTestsMixin):
    name: str = ...
    paths: set = ...
    failed_paths: list = ...
    ignore_files: bool = ...

    def __init__(
        self,
        name: str,
        *,
        paths: List = ...,
        ignore_files: List = ...
    ): ...

    def __call__(self, url: str) -> bool: ...
    @lru_cache(maxsize=10)
    def default_ignored_files(self) -> list: ...


class UrlIgnoreRegexTest(BaseURLTestsMixin):
    name: str = ...
    regex: re.Pattern = ...

    def __init__(self, name: str, *, regex: str = ...) -> str: ...
    def __call__(self, url: str) -> bool: ...


class URLPassesRegexTest(BaseURLTestsMixin):
    name: str = ...
    regex: re.Pattern = ...

    def __init__(self, name: str, *, regex: str = ...) -> str: ...
    def __call__(self, url: str) -> bool: ...


class URLGenerator:
    base_template_url: Template = ...
    urls: List = ...

    def __init__(
        self,
        template: str,
        params: dict = ...,
        k: int = ...,
        start: int = ...
    ) -> None: ...

    def __iter__(self) -> Generator: ...
    def __aiter__(self) -> Generator: ...
    def __len__(self) -> int: ...


class URLsLoader:
    data: dict[str] = ...
    _urls_to_visit: List[str] = ...
    _visited_urls: List[str] = ...

    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...

    @property
    def urls_to_visit(self) -> set[str]: ...
    @property
    def visited_urls(self) -> set[str]: ...
    def load_from_file(self) -> None: ...
    def load_from_dict(self, data) -> None: ...
