import time

from kryptone.app import BaseCrawler
from kryptone.utils.file_readers import read_document


class Jennyfer(BaseCrawler):
    """Web crawler for Kiabi. Injects javascript
    in the browser to extract data"""

    start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/'
    products = []

    def get_products(self):
        products = self.driver.get_element_by_xpath(
            '//div[contains(@class, "product-grid")]//div[contains(@class, "category-tile")]'
        )
        for product in products:
            something = 1
            yield {
                'nom': None
            }

    def run_actions(self, current_url, **kwargs):
        pass


if __name__ == '__main__':
    instance = Jennyfer()
    instance.start()
