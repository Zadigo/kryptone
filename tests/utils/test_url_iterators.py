import unittest

from kryptone.utils.urls import (URL, MultipleURLManager,
                                 URLPaginationGenerator, URLPathGenerator,
                                 URLQueryGenerator)

START_URLS = [
    'http://example.com',
    'http://example.com/1'
]


class TestURLPaginationGenerator(unittest.TestCase):
    def test_generator(self):
        instance = URLPaginationGenerator('http://example.com', k=1)
        self.assertListEqual(list(instance), ['http://example.com?page=1'])


class TestURLPathGenerator(unittest.TestCase):
    def test_generator(self):
        instance = URLPathGenerator(
            'http://example.com/$id',
            params={'id': 'number'},
            k=1,
            start=1
        )
        self.assertListEqual(list(instance), ['http://example.com/1'])


class TestURLQueryGenerator(unittest.TestCase):
    def test_generator(self):
        instance = URLQueryGenerator(
            'http://example.com/',
            param='year',
            initial_value=2001,
            end_value=2002
        )

        urls = list(instance)
        for item in urls:
            with self.subTest(item=item):
                self.assertIsInstance(item, URL)


# class TestURLQueryGenerator(unittest.TestCase):
#     def test_logic(self):
#         base_url = 'https://www.billboardmusicawards.com/winners-database/'
#         instance = URLQueryGenerator(
#             base_url, param='winnerYear',
#             initial_value=1990,
#             end_value=1992,
#             query={'winnerKeyword': None}
#         )

#         items = list(instance)
#         self.assertTrue(len(items), 2)
#         print(items)
#         for url in items:
#             with self.subTest(url=url):
#                 self.assertIn('winnerYear', url)

#     def test_step(self):
#         base_url = 'https://www.billboardmusicawards.com/winners-database/'
#         instance = URLQueryGenerator(
#             base_url, param='winnerYear',
#             initial_value=1990,
#             end_value=2000,
#             query={'winnerKeyword': None},
#             step=2
#         )
#         items = list(instance)
#         self.assertEqual(len(items), 5)


class TestMultipleURLManager(unittest.TestCase):
    """This tests a class that is not yet implemeneted on the
    spider. This class should replace the simple containers used
    to manage visisted urls, urls to visit [...] by implementing
    additional functionnalities"""

    @classmethod
    def setUpClass(cls):
        cls.start_urls = [
            'http://example.com',
            'http://example.com?page=1',
            'https://example.com/2',
            '/url-path'
        ]

    def setUp(self):
        self.instance = MultipleURLManager()
        self.populate()

    def populate(self):
        self.instance.populate(self.start_urls)
        self.assertFalse(self.instance.empty, msg='Array is empty')

        for item in self.instance.urls_to_visit:
            with self.subTest(item=item):
                self.assertIsInstance(item, URL)

        self.assertEqual(self.instance.urls_to_visit_count, 4)

        expected = URL('http://example.com')
        self.assertEqual(self.instance.next_url, expected)

    def test_structure(self):
        pass
