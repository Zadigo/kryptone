import unittest

from kryptone.routing import Router, route
from tests.items import BaseTestSpider

spider = BaseTestSpider()

ROUTES = [
    route('handle_1', regex=r'\/1', name='func1'),
    route('handle_2', path='/2', name='func2')
]


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router(ROUTES)

    def test_can_resolve(self):
        urls = [
            'http://example.com/1',
            'http://example.com/2'
        ]
        states = []
        for url in urls:
            with self.subTest(url=url):
                resolution_states = self.router.resolve(url, spider)
                states.append(resolution_states)

        for state in states:
            self.assertTrue(any(state))


if __name__ == '__main__':
    unittest.main()
