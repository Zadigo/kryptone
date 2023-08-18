import time

from kryptone import logger
from kryptone.utils.urls import URL


class MockupSpider:
    """Mockup spider used for testing
    the logic behing the main spider"""

    start_url = None
    urls_to_visit = set()
    visited_urls = set()
    list_of_seen_urls = set()

    def get_page_urls(self):
        urls = [
            'http://example/2',
            'http://example.com/1',
            'http://example.com/8'
        ]
        for url in urls:
            if url in self.urls_to_visit:
                continue

            if url in self.visited_urls:
                continue

            self.urls_to_visit.add(url)
            self.list_of_seen_urls.add(url)

    def run_actions(self, url_instance, **kwargs):
        pass

    def start(self):
        if not self.urls_to_visit:
            self.urls_to_visit.add(self.start_url)
            self.list_of_seen_urls.add(self.start_url)

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url is None:
                continue

            logger.info(f'Going to url: {current_url}')
            self.visited_urls.add(current_url)

            self.get_page_urls()

            url_instance = URL(current_url)
            self.run_actions(url_instance)

            logger.info(f"Waiting 2s")
            time.sleep(5)


class BaseTestSpider(MockupSpider):
    start_url = 'http://example.com/1'

    def handle_1(self, current_url, route=None):
        pass

    def handle_2(self, current_url, route=None):
        pass
