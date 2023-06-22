import time

from kryptone.app import BaseCrawler
from kryptone.utils.file_readers import read_document
from selenium.webdriver.common.by import By

class Jennyfer(BaseCrawler):
    """Web crawler for Kiabi. Injects javascript
    in the browser to extract data"""

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
        pass
