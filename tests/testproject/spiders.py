from kryptone.base import SiteCrawler
from kryptone import logger


class ExampleSpider(SiteCrawler):
    class Meta:
        start_urls = ['http://example.com']

    def current_page_actions(self, current_url, **kwargs):
        logger.info('Executing current page actions')
