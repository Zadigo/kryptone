import asyncio
import datetime
import mimetypes
from dataclasses import field
from urllib.parse import urlparse

import pandas
import pytz
import requests

from kryptone import logger
from kryptone.base import Performance
from kryptone.conf import settings
from kryptone.contrib.models import Product
from kryptone.utils.file_readers import write_json_document
from kryptone.utils.functions import create_filename
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.text import clean_dictionnary, slugify

TEMPORARY_PRODUCT_CACHE = set()


class EcommercePerformanceAudit(Performance):
    products_gathered: int = 0
    products_urls: list = field(default_factory=list)


class EcommerceCrawlerMixin:
    """Adds specific functionnalities dedicated
    to crawling ecommerce websites. The default model
    is `Product` which you can customize with your custom
    model"""

    scroll_step = 30
    products = []
    product_objects = []
    seen_products = []
    model = Product
    found_products_counter = 0
    product_pages = set()
    current_product_file_path = None

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        self.performance_audit = EcommercePerformanceAudit()

    def _check_products_json_file(self):
        """Checks if the products json file exist and
        creates an empty one if necessary"""
        if self.current_product_file_path is None:
            filename = f'products_{create_filename()}.json'
            self.current_product_file_path = settings.MEDIA_FOLDER / filename
            if not self.current_product_file_path.exists():
                write_json_document(self.current_product_file_path, [])

    def calculate_performance(self):
        super().calculate_performance()
        self.performance_audit.products_gathered = self.found_products_counter
        self.performance_audit.products_urls = list(TEMPORARY_PRODUCT_CACHE)

    def add_product(self, data, collection_id_regex=None, avoid_duplicates=False, duplicate_key='id_or_reference'):
        """Adds a product to the internal list product container

        >>> instance.add_product({...}, track_id=False)
        ... (True, Product)
        """
        if not data or data is None:
            logger.warning(f'Product not added to product list with {data}')
            return False, None

        data = clean_dictionnary(data)
        product = self.model(**data)

        if avoid_duplicates:
            # Creates the product but does not add it to the
            # general product list
            if product[duplicate_key] in TEMPORARY_PRODUCT_CACHE:
                return False, product

        if collection_id_regex is not None:
            product.set_collection_id(collection_id_regex)

        self.product_objects.append(product)
        self.products.append(product.as_json())

        self.found_products_counter = self.found_products_counter + 1
        TEMPORARY_PRODUCT_CACHE.add(product[duplicate_key])
        return True, product

    def as_dataframe(self, sort_by=None):
        # columns_to_keep = [
        #     'name', 'description', 'price', 'url', 'material', 'old_price',
        #     'breadcrumb', 'collection_id', 'number_of_colors',
        #     'id_or_reference', 'composition', 'color'
        # ]
        df = pandas.DataFrame(self.products)
        df = df.sort_values(sort_by or 'name')
        return df.drop_duplicates()

    def capture_product_page(self, current_url, *, product=None, element_class=None, element_id=None, prefix=None, force=False):
        """Use an element ID or element class of the current page
        to identify a product page. This will also create a
        screenshot of the page"""
        element = None
        if element_id is not None:
            element = self.driver.execute_script(
                f"""return document.querySelector('*[id="{element_id}"]')"""
            )

        if element_class is not None:
            element = self.driver.execute_script(
                f"""return document.querySelector('*[class="{element_class}"]')"""
            )

        if force or element is not None:
            self.product_pages.add(str(current_url))
            logger.info(f'{len(self.product_pages)} product pages identified')

            screen_shots_folder = settings.MEDIA_FOLDER.joinpath('screenshots')
            if not screen_shots_folder.exists():
                screen_shots_folder.mkdir()

            filename = create_filename(extension='png', suffix_with_date=True)
            if product is not None:
                filename = f'{slugify(product.name)}_{filename}'
            
            if prefix is not None:
                filename = f'{prefix}_{filename}'

            file_path = screen_shots_folder.joinpath(filename)
            self.driver.save_screenshot(file_path)
