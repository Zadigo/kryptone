import pandas
import asyncio
import mimetypes
from urllib.parse import urlparse

import requests

from kryptone import logger
from kryptone.conf import settings
from kryptone.contrib.models import Product
from kryptone.utils.file_readers import read_json_document, write_json_document
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.text import clean_dictionnary


class EcommerceCrawlerMixin:
    """Adds specific functionnalities dedicated
    to crawling ecommerce websites"""

    scroll_step = 30
    products = []
    product_objects = []
    seen_products = []
    model = Product

    def seen_products(self, using='id_or_reference'):
        """Returns a list of all products that were seen"""
        return set(map(lambda x: x[using], self.product_objects))

    def product_exists(self, product, using='id_or_reference'):
        """Checks if a product was already seen in the database"""
        if not isinstance(product, (dict, self.model)):
            raise ValueError(
                f'Value should be an instance of dict or {self.model}')
        return product[using] in self.seen_products(using=using)

    def add_product(self, data, track_id=False, collection_id_regex=None, avoid_duplicates=False, duplicate_key='id_or_reference'):
        """Adds a product to the internal product container

        >>> instance.add_product([{...}], track_id=False)
        ... (True, Product)
        """
        data = clean_dictionnary(data)
        product = self.model(**data)

        if avoid_duplicates:
            # Creates the product but does not add it to the
            # general product list
            if self.product_exists(data, using=duplicate_key):
                return False, product

        if track_id:
            product.id = self.products.count() + 1

        if collection_id_regex is not None:
            product.set_collection_id(collection_id_regex)

        self.product_objects.append(product)
        self.products.append(product.as_json())
        return True, product

    def save_product(self, data, track_id=False, collection_id_regex=None, avoid_duplicates=False, duplicate_key='id_or_reference'):
        """Adds an saves a product to the backends

        >>> instance.save_product([{...}], track_id=False)
        ... (True, Product)
        """
        # Before writing new products, ensure that we have previous
        # products from a previous scrap and if so, load the previous
        # products. This would prevent overwriting the previous file
        if not self.products:
            # TODO: Create products.json if it does not already exist
            previous_products_data = read_json_document('products.json')
            self.products = previous_products_data if previous_products_data else []
            # for item in previous_products_data:
            #     if isinstance(item, dict):
            #         self.product_objects.append(self.model(**item))
            self.product_objects = list(
                map(lambda x: self.model(**x), previous_products_data))
            message = f"Loaded {len(self.products)} products from 'products.json'"
            logger.info(message)

        new_product = self.add_product(
            data,
            track_id=track_id,
            collection_id_regex=collection_id_regex,
            avoid_duplicates=avoid_duplicates,
            duplicate_key=duplicate_key
        )
        write_json_document('products.json', self.products)
        return new_product

    def bulk_save_products(self, data, track_id=False, collection_id_regex=None):
        """Adds multiple products at once"""
        products = []
        for item in data:
            product = self.save_product(
                item, track_id=track_id, collection_id_regex=collection_id_regex)
            products.append(product)
        return products

    def save_images(self, product, path, filename=None, debug=False, quantity=None):
        """Asynchronously save images to the project's
        media folder"""
        async def main():
            urls_to_use = product.images.copy()

            # if quantity is not None:
            #     urls_to_use = [:quantity]
            
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
        columns_to_keep = [
            'name', 'description', 'price', 'url', 'material', 'old_price',
            'breadcrumb', 'collection_id', 'number_of_colors',
            'id_or_reference', 'composition', 'color'
        ]
        df = pandas.DataFrame(self.products, columns=columns_to_keep)
        df = df.sort_values(sort_by or 'name')
        return df.drop_duplicates()
