import dataclasses
import pathlib
import re
from functools import cached_property, lru_cache
from typing import NoReturn
from urllib.parse import ParseResult


class BaseModel:
    def __hash__(self) -> int: ...
    @cached_property
    def fields(self) -> list[str]: ...
    @cached_property
    def url_object(self) -> ParseResult: ...
    @cached_property
    def get_url_object(self) -> ParseResult: ...
    @cached_property
    def url_stem(self) -> str: ...
    def as_json(self) -> dict: ...
    def as_csv(self) -> list: ...


@dataclasses.dataclass
class Product(BaseModel):
    name: str
    description: str
    price: int
    url: str
    collection_id: str = None
    number_of_colors: int = 1
    id_or_reference: str = None
    id: int = None
    images: str = dataclasses.field(default_factory=[])
    color: str = None
    @cached_property
    def get_images_url_objects(self) -> list[ParseResult]: ...
    @cached_property
    def number_of_images(self) -> int: ...
    def set_collection_id(self, regex) -> NoReturn: ...
    def build_directory_from_url(self, exclude=[]) -> pathlib.Path: ...
