from selenium.webdriver.common.by import By

from kryptone.app import BaseCrawler
from kryptone.utils.file_readers import write_json_document
from kryptone.utils.text import parse_price


class Etam(BaseCrawler):
    start_url = 'https://www.etam.com/culottes-et-bas-tangas/'

    def post_visit_actions(self, **kwargs):
        self.click_consent_button(element_id='acceptAllCookies')

    # def get_products(self):
    #     product_grid = self.driver.find_element(
    #         By.CSS_SELECTOR,
    #         '.product-grid ul'
    #     )
    #     products = product_grid.find_elements(
    #         By.CSS_SELECTOR,
    #         '.grid-row'
    #     )

    #     for element in products:
    #         try:
    #             url = element.find_element(
    #                 By.CSS_SELECTOR,
    #                 'a.productCard__productImageContainer'
    #             ).get_attribute('href')
    #         except:
    #             url = None

    #         try:
    #             name = element.find_element(
    #                 By.CSS_SELECTOR,
    #                 'span.productCard__nameTitle'
    #             ).text
    #         except:
    #             name = None

    #         try:
    #             price = element.find_element(
    #                 By.CSS_SELECTOR,
    #                 'span.pageDesigner__tuileProductPrice'
    #             ).text
    #         except:
    #             name = None

    #         yield {
    #             'url': url,
    #             'name': name,
    #             'price': parse_price(price)
    #         }

    # def run_actions(self, current_url, **kwargs):
    #     self.click_consent_button(element_id='acceptAllCookies')
    #     self.scroll_page()
    #     products = list(self.get_products())
    #     write_json_document('test_etam.json', products)


if __name__ == '__main__':
    instance = Etam()
    instance.start(wait_time=4)
    # testing.start(crawl=True, run_audit=True, wait_time=2)
    # instance.resume()
