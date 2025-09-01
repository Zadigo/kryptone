import unittest

from kryptone.utils.urls import URLPaginationGenerator, URLPathGenerator, URLQueryGenerator


class TestURLPaginationGenerator(unittest.TestCase):
    def setUp(self):
        self.template = 'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/'

    def test_pagination_iterator(self):
        instance = URLPaginationGenerator(self.template, k=2)
        urls = [
            'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/?page=1',
            'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/?page=2'
        ]
        self.assertListEqual(list(instance), urls)


class TestURLPathGenerator(unittest.TestCase):
    pass


class TestURLQueryGenerator(unittest.TestCase):
    pass
