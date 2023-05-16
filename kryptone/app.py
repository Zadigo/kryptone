import os
import time
from multiprocessing import Process
from urllib.parse import urlparse

import requests
from lxml import etree
from mixins import EmailMixin, SEOMixin
from selenium.webdriver import Chrome, Edge
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from utils import RANDOM_USER_AGENT, read_json_document, write_json_document

from kryptone.kryptone import cache, logger


class BaseCrawler(SEOMixin, EmailMixin):
    start_url = None
    urls_to_visit = set()
    visited_urls = set()
    url_validators = []
    url_filters = []
    # webdriver = Chrome
    webdriver = Edge

    def __init__(self):
        path = os.environ.get('KRYPTONE_WEBDRIVER', None)
        if path is None:
            logger.instance.error('Could not find web driver')
        else:
            self._start_url_object = urlparse(self.start_url)

            # options = ChromeOptions()
            # options.add_argument(f"--proxy-server={}")

            self.driver = self.webdriver(executable_path=path)
            self.urls_to_visit.add(self.start_url)

    @property
    def get_html_page_content(self):
        return self.driver.page_source

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
            logger.instance.info(message)
        return True

    def run_filters(self, exclude=True):
        """Filters out or in urls
        included in the list of urls to visit.
        The default action is to exclude all urls that
        meet specified conditions"""
        urls_to_filter = []
        for instance in self.url_filters:
            if not urls_to_filter:
                urls_to_filter = list(filter(instance, self.urls_to_visit))
            else:
                urls_to_filter = list(filter(instance, urls_to_filter))
        logger.instance.info(
            f"Filter runned on {len(self.urls_to_visit)} - {len(urls_to_filter)} urls remaining")
        return urls_to_filter

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
        # current_page_urls = set()
        elements = self.driver.find_elements(By.TAG_NAME, 'a')
        for element in elements:
            link = element.get_attribute('href')
            link_object = urlparse(link)

            if link in self.urls_to_visit:
                continue

            if link in self.visited_urls:
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

        logger.instance.info(f"Found {len(elements)} urls")

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

    def start_from_xml(self, url):
        if not url.endswith('.xml'):
            raise ValueError()

        response = requests.get(url)
        parser = etree.XMLParser(encoding='utf-8')
        xml = etree.fromstring(response.content, parser)

    def start(self, start_urls=[], wait_time=25):
        """Entrypoint to start the web scrapper"""
        logger.instance.info('Starting Kryptone...')
        if start_urls:
            self.urls_to_visit.update(set(start_urls))

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.instance.info(
                f"{len(self.urls_to_visit)} urls left to visit")

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

            self.get_page_urls()
            self.run_actions(current_url)

            urls_data = {
                'urls_to_visit': list(self.urls_to_visit),
                'visited_urls': list(self.visited_urls)
            }
            cache.set_value('urls_data', urls_data)

            write_json_document('cache.json', urls_data)

            logger.instance.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)


class Test(BaseCrawler):
    start_url = 'http://gency313.fr/'

    def run_actions(self, current_url, **kwargs):
        emails = self.find_emails_from_text(self.get_page_text)
        # print(emails)


if __name__ == '__main__':
    t = Test()
    t.start(wait_time=10)

    try:
        process = Process(target=t.start, kwargs={'wait_time': 10})
        process.start()
        process.join()
    except:
        process.close()
