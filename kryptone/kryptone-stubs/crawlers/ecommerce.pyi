from typing import List, Literal, Tuple, dataclass_transform

import pandas

from kryptone.contrib.models import Product


class EcommerceCrawlerMixin:
    scroll_step: int = Literal[30]
    products: list = ...
    product_objects: list = ...
    seen_products: list = ...
    model: Product = ...

    def product_exists(
        self,
        product: dataclass_transform,
        using: str = 'id_or_reference'
    ) -> bool: ...

    def add_product(
        self,
        data,
        track_id: bool = ...,
        collection_id_regex: str = ...
    ) -> Tuple[bool, dataclass_transform]: ...

    def save_product(
        self,
        data: dict,
        track_id: bool = False,
        collection_id_regex: str = ...
    ) -> Tuple[bool, dataclass_transform]: ...

    def bulk_save_products(
        self,
        data,
        track_id: bool = False,
        collection_id_regex: str = ...
    ) -> List[dataclass_transform]: ...

    def save_images(
        self,
        product: dataclass_transform,
        path: str,
        filename: str = ...
    ) -> None: ...

    def as_dataframe(self, sort_by: str = ...) -> pandas.DataFrame: ...
    