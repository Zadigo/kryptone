import asyncio
import mimetypes
import pathlib
import re
from collections import deque
from urllib.parse import urlparse

import requests

from kryptone import logger
from kryptone.conf import settings
from typing import List, NoReturn, dataclass_transform
from kryptone.contrib.models import Product
from kryptone.utils.file_readers import read_json_document, write_json_document
from kryptone.utils.randomizers import RANDOM_USER_AGENT


class EcommerceCrawlerMixin:
    scroll_step = 30
    products = []
    product_objects = []
    seen_products = []
    model = Product

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
    ) -> dataclass_transform: ...

    def save_product(
        self, 
        data: dict, 
        track_id: bool = False,
        collection_id_regex: str = ...
    ) -> dataclass_transform: ...

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
    ) -> NoReturn: ...
