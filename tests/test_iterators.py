import unittest

from kryptone.utils.iterators import PagePaginationGenerator, URLIterator
from kryptone.utils.urls import URL

START_URLS = [
    'http://example.com',
    'http://example.com/1'
]


class TestPagination(unittest.TestCase):
    def test_generation(self):
        instance = PagePaginationGenerator('http://example.com', k=1)
        self.assertListEqual(list(instance), ['http://example.com?page=1'])

    def test_addition(self):
        instance1 = PagePaginationGenerator('http://example.com', k=1)
        instance2 = PagePaginationGenerator('http://google.com', k=1)
        combinator = instance1 + instance2
        self.assertListEqual(
            combinator.urls, 
            ['http://example.com?page=1', 'http://google.com?page=1']
        )


class TestUrlIterator(unittest.TestCase):
    def setUp(self):
        self.instance = URLIterator(start_urls=START_URLS)

    def test_loop(self):
        while not self.instance.empty:
            url = self.instance.get()
            with self.subTest(url=url):
                self.assertIsInstance(url, URL)

    def test_append(self):
        self.instance.append('http://google.com')
        self.assertFalse(self.instance.empty)
        self.assertIn('http://google.com', self.instance)
        self.assertTrue(len(self.instance) == 3)

    def test_get(self):
        url = self.instance.get()
        self.assertIsInstance(url, URL)
        self.assertTrue(self.instance.urls_to_visit_count, 1)

    def test_appendleft(self):
        url = 'http://google.com'
        self.instance.appendleft(url)
        self.assertTrue(self.instance[0], url)


if __name__ == '__main__':
    unittest.main()
