"""
This is a blackbox used to the test the
integrity of the crawler classes
"""

from selenium.webdriver.common.by import By

from kryptone.base import BaseCrawler
from kryptone.utils.file_readers import write_json_document
from kryptone.utils.text import parse_price


class Etam(BaseCrawler):
    start_url = 'https://www.etam.com/culottes-et-bas-tangas/'
    browser_name = 'Edge'

    def post_visit_actions(self, **kwargs):
        self.click_consent_button(element_id='acceptAllCookies')

    def run_actions(self, current_url, **kwargs):
        self.save_to_local_storage('url', current_url)


if __name__ == '__main__':
    instance = Etam()
    instance.start(wait_time=10)
