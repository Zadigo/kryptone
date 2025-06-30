import unittest
from unittest.mock import Mock, patch

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
            'https://example.com',
            'https://example.com?page=1',
            'https://example.com/2',
            '/url-path'
        ]

        cls.other_urls = [
            'https://example.com/bershka'
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

        urls_count = len(self.start_urls)
        self.assertEqual(self.instance.urls_to_visit_count, urls_count)

        # expected = URL('https://example.com/2')
        # self.assertEqual(self.instance.next_url, expected)

        # expected_start_url = URL('https://example.com')
        # self.assertEqual(self.instance.s, expected_start_url)

    def test_add_urls(self):
        self.instance.add_urls(self.other_urls)

        # 5
        urls_count = len(self.start_urls) + len(self.other_urls)
        self.assertEqual(len(self.instance.list_of_seen_urls), urls_count)
        self.assertTrue(len(self.instance._urls_to_visit) > 0)
        self.assertTrue(
            len(self.instance._urls_to_visit) == urls_count,
            msg=f'urls to visit: {len(self.instance._urls_to_visit)}'
        )

        for item in self.instance._urls_to_visit:
            with self.subTest(item=item):
                self.assertIsInstance(item, URL)

    def test_add_urls_not_in_domain(self):
        none_valid_url = URL('http://bershka.com')
        self.instance.add_urls([none_valid_url])
        self.assertNotIn(none_valid_url, self.instance._urls_to_visit)

    @patch('kryptone.utils.urls.URLIgnoreTest')
    def test_with_custom_filter(self, mock_ignore_test: Mock):
        mock_ignore_test.side_effect = lambda url: False

        self.instance.custom_url_filters = [mock_ignore_test]
        urls = self.instance.run_url_filters(self.start_urls[:1])

        mock_ignore_test.assert_called_once()
        mock_ignore_test.assert_called_once_with('https://example.com')
        self.assertTrue(len(urls) > 0)

    def test_get(self):
        url = self.instance.get()
        self.assertIsInstance(url, URL)
        self.assertEqual(url, self.instance._current_url)
        self.assertEqual(self.instance.urls_to_visit_count, 3)
        self.assertEqual(self.instance.current_iteration, 1)
        self.assertIsInstance(self.instance._current_url, URL)
