import os
import time
from multiprocessing import Process
from urllib.parse import urlparse

import requests
from lxml import etree
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from kryptone import cache, logger, settings
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.utils.file_readers import (read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.randomizers import RANDOM_USER_AGENT


class BaseCrawler(SEOMixin, EmailMixin):
    start_url = None
    urls_to_visit = set()
    visited_urls = set()
    url_validators = []
    url_filters = []
    webdriver = Chrome
    # webdriver = Edge

    def __init__(self):
        path = os.environ.get('KRYPTONE_WEBDRIVER', None)
        if path is None:
            logger.error('Could not find web driver')
        else:
            self._start_url_object = urlparse(self.start_url)

            # options = EdgeOptions()
            options = ChromeOptions()
            options.add_argument('--remote-allow-origins=*')
            # options.add_argument(f"--proxy-server={}")

            self.driver = self.webdriver(
                executable_path=path,
                options=options
            )
            self.urls_to_visit.add(self.start_url)

    @property
    def get_html_page_content(self):
        return self.driver.page_source

    @property
    def get_page_link_elements(self):
        return self.driver.find_elements(By.TAG_NAME, 'a')

    def build_headers(self, options):
        headers = {
            'User-Agent': RANDOM_USER_AGENT(),
            'Accept-Language': 'en-US,en;q=0.9'
        }
        items = [f"--header={key}={value})" for key, value in headers.items()]
        options.add_argument(' '.join(items))

    def run_validators(self, url):
        """Validates an url before it is
        included in the list of urls to visit"""
        results = []
        if self.url_validators:
            for validator in self.url_validators:
                if not callable(validator):
                    continue

                result = validator(url, driver=self.driver)
                if result is None:
                    result = False
                results.append(result)
            test_result = all(results)

            if test_result:
                message = f"Validation successful for {url}"
            else:
                message = f"Validation failed for {url}"
            logger.info(message)
        return True

    def run_filters(self, exclude=True):
        """Filters out or in urls
        included in the list of urls to visit.
        The default action is to exclude all urls that
        meet specified conditions"""
        # Ensure that we return the original
        # urls to visit if there are no filters
        # or this might return nothing
        if self.url_filters:
            urls_to_filter = []
            for instance in self.url_filters:
                if not urls_to_filter:
                    urls_to_filter = list(filter(instance, self.urls_to_visit))
                else:
                    urls_to_filter = list(filter(instance, urls_to_filter))
            logger.info(
                f"Filter runned on {len(self.urls_to_visit)} urls / {len(urls_to_filter)} urls remaining"
            )
            return urls_to_filter
        return self.urls_to_visit

    def scroll_to(self, percentage=80):
        percentage = percentage / 100
        script = f"""
        const height = document.body.scrollHeight;
        const pixels = Math.round(height * {percentage});
        window.scrollTo(0, pixels);
        """
        self.driver.execute_script(script)

    def scroll_window(self):
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

    def get_page_urls(self, same_domain=True):
        elements = self.get_page_link_elements
        for element in elements:
            link = element.get_attribute('href')
            link_object = urlparse(link)

            if link in self.urls_to_visit:
                continue

            if link in self.visited_urls:
                continue

            if link is None or link == '':
                continue

            # Links such as http://exampe.com/path#
            # are useless and repetitive
            if link.endswith('#'):
                continue

            if link_object.netloc != self._start_url_object.netloc:
                continue

            # If the url contains a fragment, it's the same
            # as visiting the root element of that page
            # e.g. example.com/#google == example.com/
            if link_object.fragment:
                continue

            # If we already visited the home page then
            # skip all urls that include this home page
            if link_object.path == '/' and self._start_url_object.path == '/':
                continue

            # Reconstruct a partial url e.g. /google -> https://example.com/google
            if link_object.path != '/' and link.startswith('/'):
                link = f'{self._start_url_object.scheme}://{self._start_url_object.netloc}{link}'

            self.urls_to_visit.add(link)

        # TODO: Filter pages that we do not want to visit
        self.urls_to_visit = set(self.run_filters())

        logger.info(f"Found {len(elements)} urls")

    def run_actions(self, current_url, **kwargs):
        """Run additional actions of the currently
        visited web page"""

    def resume(self, **kwargs):
        """From a previous list of urls to visit and
        visited urls, resume web scrapping"""
        data = read_json_document('cache.json')
        self.urls_to_visit = data['urls_to_visit']
        self.visited_urls = data['visited_urls']
        self.start(**kwargs)

    def start_from_xml(self, url, **kwargs):
        if not url.endswith('.xml'):
            raise ValueError()

        response = requests.get(url)
        parser = etree.XMLParser(encoding='utf-8')
        xml = etree.fromstring(response.content, parser)
        self.start(start_urls=[], **kwargs)

    def start(self, start_urls=[], wait_time=25, language='en', crawl=True):
        """Entrypoint to start the web scrapper"""
        logger.info('Started crawling...')
        if start_urls:
            self.urls_to_visit.update(set(start_urls))

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(
                f"{len(self.urls_to_visit)} urls left to visit"
            )

            current_url_object = urlparse(current_url)
            # If we are not the same domain as the start
            # url, stop, since we are not interested in
            # exploring the whole internet
            if current_url_object.netloc != self._start_url_object.netloc:
                continue

            self.driver.get(current_url)

            wait = WebDriverWait(self.driver, 5)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            self.visited_urls.add(current_url)

            # We can either crawl all the website
            # or just crawl a specific page on
            # the website
            if crawl:
                self.get_page_urls()
            self.run_actions(current_url)

            urls_data = {
                'urls_to_visit': list(self.urls_to_visit),
                'visited_urls': list(self.visited_urls)
            }
            cache.set_value('urls_data', urls_data)

            write_json_document('cache.json', urls_data)

            # Audit the website TODO: Improve the way in
            # in which the text is extracted from the page
            # self.audit_page(current_url, language=language)
            # vocabulary = self.global_audit(language=language)
            # write_json_document('audit.json', self.page_audits)
            # write_json_document('global_audit.json', vocabulary)

            cache.set_value('page_audits', self.page_audits)
            # cache.set_value('global_audit', vocabulary)

            self.emails(
                self.get_page_text,
                elements=self.get_page_link_elements
            )
            write_csv_document('emails.csv', self.emails_container)

            logger.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)


# class Kiabi(BaseCrawler):
#     start_url = 'https://www.kiabi.com/femme_200005'
#     products = []

#     def _products(self, unique=False):
#         """Returns a list of unique products
#         from the page"""
#         unique_products = set()
#         result = []
#         for item in self.products:
#             items = item.get_items()

#             if item.name in unique_products:
#                 continue

#             result.append(items)
#             unique_products.add(item.name)
#         return result

#     def _poll_products(self):
#         """Polls the page for new products 
#         continuously as we keep scrolling
#         down the rest of the page"""
#         from kryptone.db.models import Product

#         results = self.driver.execute_script("""
#         // Select the containers for the different products
#         const a = document.querySelectorAll('div[class^="productCard_productCardContainer"]')

#         // Parse each products
#         return Array.from(a).map((productCard) => {
#             var product = {
#                 url: null,
#                 name: null,
#                 old_price: null,
#                 new_price: null
#             }
#             var h2 = productCard.querySelector('h2')
#             var spanElements = productCard.getElementsByTagName('span')

#             if (h2) {
#                 product.name = h2.innerText
#             }
#             product.url = productCard.querySelector('a').href

#             // Sometimes we have two prices: discounted, original
#             var firstPrice = productCard.querySelector('div[data-testid="productListCardInformations"] span[data-testid="productList_span_cardPrice"] span:first-of-type')
#             var lastPrice = productCard.querySelector('div[data-testid="productListCardInformations"] span[data-testid="productList_span_cardPrice"] span:last-of-type')

#             if (firstPrice) {
#                 product.old_price = firstPrice.innerText
#             }

#             if (lastPrice) {
#                 product.new_price = lastPrice.innerText
#             }

#             return product
#         })
#         """)
#         for result in results:
#             product = Product(**result)
#             self.products.append(product)

#     def run_actions(self, current_url, **kwargs):
#         # button[0].scrollIntoView()
#         self.driver.execute_script("""
#         // Clicks on the button to load more products
#         const xpath = '//div[@class="productList_buttonContainer__WURDD"]/button'
#         const button = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
#         button.click()
#         """)

#         base = 8000
#         for _ in range(1000):
#             self.driver.execute_script(f'window.scroll(0, {base})')
#             base = base + 2000
#             time.sleep(10)
#             self._poll_products()
#             write_json_document('kiabi.json', self._products(unique=True))


# if __name__ == '__main__':
#     t = Kiabi()
#     t.start(wait_time=10, crawl=False)

#     # try:
#     #     process = Process(target=t.start, kwargs={'wait_time': 15})
#     #     process.start()
#     #     process.join()
#     # except:
#     #     process.close()
