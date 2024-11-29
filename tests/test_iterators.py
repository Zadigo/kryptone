import unittest
from kryptone.utils.urls import URLPaginationGenerator, URLPathGenerator, URLQueryGenerator

START_URLS = [
    'http://example.com',
    'http://example.com/1'
]


class TestPagination(unittest.TestCase):
    def test_generator(self):
        instance = URLPaginationGenerator('http://example.com', k=1)
        self.assertListEqual(list(instance), ['http://example.com?page=1'])


class TestURLPathGenerator(unittest.TestCase):
    def test_generator(self):
        instance = URLPathGenerator(
            'http://example.com/$id',
            params={'id': 'number'},
            k=1
        )
        self.assertListEqual(list(instance), ['http://example.com/1'])


class TestURLQueryGenerator(unittest.TestCase):
    def test_generator(self):
        instance = URLQueryGenerator(
            'http://example.com/',
            param='year',
            param_values=['2001', '2002']
        )

        self.assertListEqual(
            list(instance),
            [
                'http://example.com/?year=2001',
                'http://example.com/?year=2002'
            ]
        )
