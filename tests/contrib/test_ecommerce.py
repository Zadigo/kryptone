# import dataclasses
# import unittest

# import pandas

# from kryptone.contrib.crawlers.ecommerce import EcommerceCrawlerMixin
# from kryptone.utils.functions import directory_from_breadcrumbs

# DATA = {
#     'name': 'Google',
#     'id_or_reference': 1,
#     'breadcrumb': 'stars > KENDALL',
#     'price': '1',
#     'description': 'Something',
#     'url': 'http://example.com/something-1',
#     'images': [
#         'https://dfcdn.defacto.com.tr/7/B2467AX_23AU_NV241_01_01.jpg'
#     ]
# }


# class TestEcommerceContrib(unittest.TestCase):
#     def setUp(self):
#         self.instance = EcommerceCrawlerMixin()

#     def test_save_product(self):
#         state, product = self.instance.save_product(DATA)
#         self.assertTrue(state)
#         self.assertTrue(dataclasses.is_dataclass(product))

#     def test_product_exists(self):
#         self.instance.add_product(DATA)
#         state, _ = self.instance.add_product(DATA, avoid_duplicates=True)
#         self.assertFalse(state)

#     def test_save_images(self):
#         state, product = self.instance.add_product(DATA)
#         self.instance.save_images(
#             product,
#             directory_from_breadcrumbs(product.breadcrumb)
#         )

#     def test_dataframe(self):
#         self.instance.add_product(DATA)
#         self.assertIsInstance(self.instance.as_dataframe(), pandas.DataFrame)
