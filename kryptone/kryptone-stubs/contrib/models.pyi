import dataclasses
from functools import cached_property
from typing import Any, Literal
from urllib.parse import ParseResult


class BaseModel:
    def __getitem__(self, key) -> Any: ...

    @cached_property
    def fields(self) -> list[str]: ...

    @cached_property
    def get_url_object(self) -> ParseResult: ...

    @cached_property
    def url_stem(self) -> str: ...

    def as_json(self) -> dict[str, Any]: ...
    def as_csv(self) -> list: ...


@dataclasses.dataclass
class Products(BaseModel):
    name: str
    price: str
    url: str
    image: str = None
    colors: list = dataclasses.field(default=list)
    other_information: str = None


@dataclasses.dataclass
class Product(BaseModel):
    name: str
    description: str
    price: int
    url: str
    material: str = None
    discount_price: int = None
    breadcrumb: str = ...
    collection_id: str = ...
    number_of_colors: Literal[1] = 1
    id_or_reference: str = None
    images: list = dataclasses.field(default_factory=list)
    composition: str = None
    color: str = ...
    date: str = ...
    sizes: list = dataclasses.field(default_factory=list)
    out_of_stock: bool = ...
    inventory: str = None
    is_404: bool = False

    def __hash__(self) -> int: ...

    @cached_property
    def get_images_url_objects(self) -> list[ParseResult]: ...

    @cached_property
    def number_of_images(self) -> int: ...

    def set_collection_id(self, regex: str) -> None: ...
    def complex_name(self) -> str: ...


@dataclasses.dataclass
class GoogleSearch:
    title: str
    url: str
