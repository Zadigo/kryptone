import time


class EcommerceCrawlerMixin:
    """Adds specific functionnalities dedicated
    to crawling ecommerce websites"""

    scroll_step = 30
    products = []
    product_objects = []
    
    def add_product(self, item):
        self.product_objects.append(item)
        self.products.append(item.as_json())

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
