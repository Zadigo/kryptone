import asyncio
import datetime
import mimetypes
import pathlib
from urllib.parse import urlparse

import pandas
import pytz
import requests

from kryptone import logger
from kryptone.conf import settings
from kryptone.contrib.models import Product
from kryptone.utils.file_readers import (get_media_folder, read_json_document,
                                         write_json_document)
from kryptone.utils.functions import create_filename
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.text import clean_dictionnary, slugify

TEMPORARY_PRODUCT_CACHE = set()


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
        self.statistics.update({
            'products_gathered': self.found_products_counter,
            'products_urls': list(TEMPORARY_PRODUCT_CACHE)
        })

    def add_product(self, data, collection_id_regex=None, avoid_duplicates=False, duplicate_key='id_or_reference'):
        """Adds a product to the internal list product container

        >>> instance.add_product({...}, track_id=False)
        ... (True, Product)
        """
        if not data or data is None:
            logger.warning(f'Product not added to product list with {data}')
            return False

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

    def save_product(self, data, collection_id_regex=None, avoid_duplicates=False, duplicate_key='id_or_reference'):
        """Adds a single product data gathered from the website to the
        underlying container and then creates a file called `products_xyz.json`
        in the current project's media folder

        >>> instance.save_product([{...}], track_id=False)
        ... (True, Product)
        """
        if data is None:
            logger.warning('Received None when trying to save a product')
            return (False, None)
        
        if 'date' not in data:
            data['date'] = datetime.datetime.now(tz=pytz.UTC)

        self._check_products_json_file()

        new_product = self.add_product(
            data,
            collection_id_regex=collection_id_regex,
            avoid_duplicates=avoid_duplicates,
            duplicate_key=duplicate_key
        )
        write_json_document(self.current_product_file_path, self.products)
        return new_product
    
    def bulk_add_products(self, data, collection_id_regex=None):
        """Adds multiple products to the internal list product container

        >>> instance.add_product([{...}], track_id=False)
        ... (True, Product)
        """
        products = []
        for item in data:
            state, product = self.add_product(
                item, 
                collection_id_regex=collection_id_regex
            )
            products.append(product)
        return products

    def bulk_save_products(self, data=None, collection_id_regex=None):
        """Adds multiple products at once to the underlying container
        if data is provided otherwise will save the current stored products
        to the `products_xyz.json` file"""
        products = []
        if data is not None:
            self.bulk_add_products(data)
        self._check_products_json_file()
        write_json_document(self.current_product_file_path, self.products)
        return products

    def save_images(self, product, path, filename=None, download_first=False):
        """Asynchronously save images to the project's
        media folder. Only one image could be downloaded using
        the `download_first` parameter"""
        async def main():
            urls_to_use = product.images.copy()

            if download_first:
                urls_to_use = urls_to_use[:1]

            queue = asyncio.Queue()

            async def request_image():
                while urls_to_use:
                    url = urls_to_use.pop()
                    headers = {'User-Agent': RANDOM_USER_AGENT()}

                    try:
                        response = requests.get(url, headers=headers)
                    except Exception as e:
                        logger.error(f'Failed to fetch image data: {url}')
                        logger.error(e)
                    else:
                        url_object = urlparse(url)

                        if response.status_code == 200:
                            # Guess the extension of the image that we
                            # want to save locally
                            mimetype, _ = mimetypes.guess_type(url_object.path)
                            extension = mimetypes.guess_extension(
                                mimetype,
                                strict=True
                            )

                            await queue.put((extension, response.content))
                        else:
                            logger.error(f'Image request error: {url}')
                    finally:
                        await asyncio.sleep(1)

            async def save_image():
                index = 1
                while not queue.empty():
                    extension, content = await queue.get()
                    name = filename or product.url_stem
                    # We'll create directories that map the url
                    # path structure. It's the easiest way to
                    # find images in the local folder based
                    # on the path the website's url
                    # TEST: Instead of using the index below, we
                    # can also create directory with product reference
                    # that we retrieved from the url. Then generate
                    # random names for the images
                    directory_path = settings.MEDIA_FOLDER / path
                    if not directory_path.exists():
                        directory_path.mkdir(parents=True)

                    final_path = directory_path.joinpath(
                        f'{name}_{index}{extension}'
                    )
                    with open(final_path, mode='wb') as f:
                        if content is not None:
                            f.write(content)
                        index = index + 1

                    logger.info(f"Downloaded image: '{final_path}'")
                    # Delay this task slightly more than the
                    # one above to allow requests to populate
                    # the queue on time
                    await asyncio.sleep(3)

            await asyncio.gather(request_image(), save_image())

        asyncio.run(main())

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
