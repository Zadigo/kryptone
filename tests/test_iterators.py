import unittest

from kryptone.utils.urls import URL, URLIterator

START_URLS = [
    'http://example.com',
    'http://example.com/1'
]


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
