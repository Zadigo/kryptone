import time

from selenium.webdriver import Edge
from selenium.webdriver.common.by import By

from kryptone.base import BaseCrawler


class Jennyfer(BaseCrawler):
    webdriver = Edge
    start_url = 'https://www.jennyfer.com/fr-fr/vetements/maillots-de-bain/'

    def post_visit_actions(self, **kwargs):
        self.click_consent_button(element_id='onetrust-accept-btn-handler')

        time.sleep(1)

        try:
            download_app_button = self.driver.find_element(
                By.CSS_SELECTOR,
                'svg[class="qlf-close-button__svg"]'
            )
            download_app_button.click()
        except:
            pass

    def get_products(self):
        return []

    def run_actions(self, current_url, **kwargs):
        self.scroll_window()
