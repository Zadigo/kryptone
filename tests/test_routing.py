# import unittest

# from kryptone.routing import Router, route
# from kryptone.base import SiteCrawler


class TestSpider(SiteCrawler):
    class Meta:
        debug_mode = True

#     def handle_1(self, current_url, **kwargs):
#         pass

#     def handle_2(self, current_url, **kwargs):
#         pass


# class TestRouter(unittest.TestCase):
#     @classmethod
#     def setUpClass(cls):
#         cls.spider = TestSpider()

#     def setUp(self):
#         routes = [
#             route('handle_1', regex=r'\/1', name='func1'),
#             route('handle_2', path='/2', name='func2')
#         ]
#         self.router = Router(routes)

#     def test_can_resolve(self):
#         urls = [
#             'http://example.com/1',
#             'http://example.com/2'
#         ]
#         states = []
#         for url in urls:
#             with self.subTest(url=url):
#                 resolution_states = self.router.resolve(url, self.spider)
#                 states.append(resolution_states)

#         for state in states:
#             self.assertTrue(any(state))
