from urllib.parse import quote, urlencode
from kryptone.base import SiteCrawler


class GoogleSearchMixin(SiteCrawler):
    start_url = "https://www.google.com/search?q=site%3Alinkedin.com%2Fin+Undiz"
    # start_url = 'https://www.google.com/search'
    # query = 'site:linkedin.com/in Undiz'

    class Meta:
        crawl = False

    def get_start_url(self):
        query = quote(self.query)
        encoded_query = urlencode({'q': query})
        return f'{self.start_url}?{encoded_query}'

    def run_actions(self):
        pass
