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

from kryptone import logger
from kryptone.cache import Cache
from kryptone.conf import settings
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.utils.file_readers import (read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.randomizers import RANDOM_USER_AGENT

cache = Cache()


class ActionsMixin:
    @property
    def scrolled_to_bottom(self):
        """Checks that we have scrolled to the bottom of the page"""
        script = """
        // The scroll element does not go that far down after
        // a moment so adjust the scrollHeight number by reducing
        // it by  a 100
        return (window.innerHeight + window.scrollY) >= (document.documentElement.scrollHeight - 100)
        """
        return self.driver.execute_script(script)
    
    def scroll_page(self, pixels=2000):
        """Continuously scroll the current page
        in order to load a set of products"""
        new_pixels = pixels
        is_scrollable = True
        while is_scrollable:
            self.scroll_window(pixels=new_pixels)
            is_scrollable = True if not self.scrolled_to_bottom else False
            time.sleep(3)
            # Increment the number of pixels to
            # accomplish scrolling the whole page
            new_pixels = new_pixels + pixels

    
    def scroll_to(self, percentage=80):
        """Scroll to a specific section of the page"""
        percentage = percentage / 100
        script = f"""
        const height = document.body.scrollHeight
        const pixels = Math.round(height * {percentage});
        window.scrollTo(0, pixels);
        """
        self.driver.execute_script(script)

    def scroll_window(self, pixels=2000):
        """Scroll the whole window"""
        # script = "window.scrollTo(0, document.body.scrollHeight)"
        script = f"window.scrollTo(0, {pixels})"
        self.driver.execute_script(script)


class BaseCrawler(ActionsMixin, SEOMixin, EmailMixin):
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
            if not isinstance(self.start_url, str):
                raise ValueError('Start url must be a string')
            self._start_url_object = urlparse(self.start_url)

            # options = EdgeOptions()
            options = ChromeOptions()
            options.add_argument('--remote-allow-origins=*')
            options.add_argument(f'user-agent={RANDOM_USER_AGENT()}')
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
    
    @property
    def completion_percentage(self):
        result = len(self.visited_urls) / len(self.urls_to_visit)
        return round(result, 0)

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

    def start(self, start_urls=[], wait_time=25, run_audit=False, language='en', crawl=True):
        """Entrypoint to start the web scrapper"""
        logger.info('Started crawling...')
        if start_urls:
            self.urls_to_visit.update(set(start_urls))

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(
                f"{len(self.urls_to_visit)} urls left to visit"
            )

            if self.start_url is None:
                self.start_url = current_url

            current_url_object = urlparse(current_url)
            # If we are not the same domain as the start
            # url, stop, since we are not interested in
            # exploring the whole internet
            if current_url_object.netloc != self._start_url_object.netloc:
                continue

            self.driver.get(current_url)

            wait = WebDriverWait(self.driver, 8)
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

            if run_audit:
                # Audit the website TODO: Improve the way in
                # in which the text is extracted from the page
                self.audit_page(current_url, language=language)
                vocabulary = self.global_audit(language=language)
                write_json_document('audit.json', self.page_audits)
                write_json_document('global_audit.json', vocabulary)

                cache.set_value('page_audit', self.page_audits)
                # cache.set_value('global_audit', vocabulary)
                logger.info('Audit completed...')

            self.emails(
                self.get_page_text,
                elements=self.get_page_link_elements
            )
            write_csv_document('emails.csv', self.emails_container)

            logger.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)
