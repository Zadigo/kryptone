import time

from kryptone.app import BaseCrawler
from kryptone.utils.file_readers import read_document


class Jennyfer(BaseCrawler):
    """Web crawler for Kiabi. Injects javascript
    in the browser to extract data"""

    start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/'
    products = []

    def get_products(self):
        return []

    def run_actions(self, current_url, **kwargs):
        pass


if __name__ == '__main__':
    instance = Jennyfer()
    instance.start()