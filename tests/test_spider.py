import unittest

from tests.items import BaseTestSpider


class TestSpider(unittest.TestCase):
    def test_loop(self):
        spider = BaseTestSpider()
        spider.start()
        expected_urls = set([
            'http://example/2',
            'http://example.com/1',
            'http://example.com/8'
        ])
        self.assertSetEqual(spider.visited_urls, expected_urls)
        self.assertTrue(len(spider.visited_urls) == len(expected_urls))
        # self.assertTrue(len(spider.list_of_seen_urls) == 2)


if __name__ == '__main__':
    unittest.main()
