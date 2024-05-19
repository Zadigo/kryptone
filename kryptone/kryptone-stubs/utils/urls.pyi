import pathlib
import re
from functools import lru_cache
from typing import DefaultDict, List, Tuple, Union, override
from urllib.parse import ParseResult


@lru_cache(maxsize=100)
def load_image_extensions() -> list[str]: ...


class URL:
    raw_url: str = ...
    url_object: ParseResult = ...

    def __init__(self, url_string: str): ...
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
