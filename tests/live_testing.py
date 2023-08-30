import time
from kryptone.mixins import SEOMixin

class BaseLiveTestSpider(SEOMixin):
    def __init__(self):
        from kryptone.base import get_selenium_browser_instance
        self.driver = get_selenium_browser_instance(browser_name='Edge')
        self.driver.get('https://www.topo-lab.fr/topo-innov/')

    def __del__(self):
        self.driver.quit()


live = BaseLiveTestSpider()
live.audit_page(live.driver.current_url)
