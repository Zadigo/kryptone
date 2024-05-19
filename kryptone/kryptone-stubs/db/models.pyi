import dataclasses
import pandas
from urllib.parse import unquote, urlparse
import pathlib
from functools import cached_property
from typing import Any, List
from urllib.parse import ParseResult


class BaseModel:
    def __getitem__(self, key: str) -> Any: ...

    @cached_property
    def fields(self) -> List[str]: ...
    @cached_property
    def get_url_object(self) -> ParseResult: ...
    @cached_property
    def url_stem(self) -> str: ...
    def as_json(self) -> dict: ...
    def as_csv(self) -> list: ...
