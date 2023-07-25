import asyncio
import mimetypes
from urllib.parse import urlparse

import requests

from kryptone.conf import settings
from kryptone.contrib.models import Product
from kryptone.utils.randomizers import RANDOM_USER_AGENT


class EcommerceCrawlerMixin:
    """Adds specific functionnalities dedicated
    to crawling ecommerce websites"""

    # TEST:

    scroll_step = 30
    products = []
    product_objects = []
    
    def add_product(self, data):
        product_object = Product(**data)
        self.product_objects.append(product_object)
        self.products.append(product_object.as_json())
        return product_object

    def save_images(self, product, path, filename=None):
        """Asynchronously save images to the project's
        media folder"""
        urls_to_use = product.urls.copy()
        queue = asyncio.Queue()

        async def request_image():
            while urls_to_use:
                url = urls_to_use.pop()
                headers = {'User-Agent': RANDOM_USER_AGENT()}
                response = requests.get(url, headers=headers)

                url_object = urlparse(url)

                mimetype = mimetypes.guess_type(url_object.path)
                extension = mimetypes.guess_extension(mimetype)

                if response.status_code == 200:
                    await queue.put((extension, response.content))
                    await asyncio.wait(1)
        
        async def save_image():
            index = 1
            while not queue.empty():
                extension, content = await queue.get()
                name = filename or f'{path}{product.url_stem}_{index}{extension}'
                full_path = settings.MEDIA_FOLDER.join(name)
                with open(full_path, mode='wb') as f:
                    if content is not None:
                        f.write(content)
                        index = index + 1
        
        asyncio.gather(request_image, save_image)

    # def scroll_page(self):
    #     can_scroll = True
    #     previous_scroll_position = None
    #     while can_scroll:
    #         script = f"""
    #         // Scrolls the whole page of a website
    #         const documentHeight = document.documentElement.offsetHeight
    #         let currentPosition = document.documentElement.scrollTop

    #         const scrollStep = Math.ceil(documentHeight / {self.scroll_step})
    #         currentPosition += scrollStep
    #         document.documentElement.scroll(0, currentPosition)
    #         return [documentHeight, currentPosition]
    #         """
    #         result = self.driver.execute_script(script)
    #         document_height, scroll_position = result
    #         if scroll_position is not None and scroll_position == previous_scroll_position:
    #             can_scroll = False
    #         previous_scroll_position = scroll_position
    #         time.sleep(2)
