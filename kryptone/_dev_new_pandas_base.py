from kryptone._new_pandas_base import SiteCrawler


class AnotherSpider(SiteCrawler):
    # start_url = 'https://www.etam.com/p/tanga-en-tulle-654703722.html'
    start_url = 'http://gency313.fr'

    class Meta:
        debug_mode = False


c = AnotherSpider(browser_name='Edge')
c.start()
