import unittest
import dataclasses
from kryptone.contrib.crawlers.ecommerce import EcommerceCrawlerMixin


class TestEcommerceContrib(unittest.TestCase):
    def setUp(self):
        self.instance = EcommerceCrawlerMixin()

    def test_save_product(self):
        data = {
            'name': 'Google',
            'price': '1',
            'description': 'Something',
            'url': 'http://example.com',
            'images': [
                'http://google.com'
            ]
        }
        state, product = self.instance.save_product(data)
        self.assertTrue(state)
        self.assertTrue(dataclasses.is_dataclass(product))


if __name__ == '__main__':
    unittest.main()
