import pathlib
from typing import Any, List, Literal, Tuple

import pandas

from kryptone.contrib.models import Product
from kryptone.utils.urls import URL

TEMPORARY_PRODUCT_CACHE: set[str] = ...


class EcommerceCrawlerMixin:
    scroll_step: int = Literal[30]
    products: List = ...
    product_objects: List = ...
    seen_products: List = ...
    model: Product = ...
    found_products_counter: int = ...
    product_pages: set = ...
    current_product_file_path: pathlib.Path = ...

    def _check_products_json_file(self) -> None: ...

    def calculate_performance(self) -> None: ...

    def add_product(
        self,
        data: dict[str, Any],
        collection_id_regex: str = ...,
        avoid_duplicates: bool = ...,
        duplicate_key: str = ...
    ) -> Tuple[bool, Product]: ...

    def save_product(
        self,
        data: dict[str, Any],
        collection_id_regex: str = ...,
        avoid_duplicates: bool = ...,
        duplicate_key: str = ...
    ) -> Union[Tuple[bool, Product], Tuple[bool, None]]: ...
    
    def bulk_add_products(
        self, 
        data: list[dict[str, Any]], 
        collection_id_regex: str=...
    ) -> list[Product]:
    
    def bulk_save_products(
        self,
        data: list[dict[str, Any]],
        collection_id_regex: str = ...
    ) -> List[Product]: ...

    def save_images(
        self,
        product: Product,
        path: str,
        filename: str = ...,
        download_first: bool = ...
    ) -> None: ...

    def as_dataframe(
        self, 
        sort_by: str = ...
    ) -> pandas.DataFrame:

    def capture_product_page(
        self,
        current_url: URL,
        *,
        product: Product = ...,
        element_class: str = ...,
        element_id: str = ...,
        prefix: str = ...,
        force: bool = ...
    ) -> None: ...
