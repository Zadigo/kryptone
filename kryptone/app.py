import os
import random
import string
import time
from multiprocessing import Process
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from lxml import etree
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from kryptone import logger
from kryptone.cache import Cache
from kryptone.conf import settings
from kryptone.db import backends
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.signals import Signal
from kryptone.utils.file_readers import (read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URLFile

# post_init = Signal()
# navigation = Signal()
db_signal = Signal()

cache = Cache()


class ActionsMixin:
     # Default speed at which the robot
    # should scroll a given page
    default_scroll_step = 80

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
        in order to load a set of products. This function
        will scroll the window as long as the position
        has not reached the bottom of the page"""
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

    def click_consent_button(self, element_id=None, element_class=None):
        """Click the consent to cookies button which often
        tends to appear on websites"""
        element = None
        if element_id is not None:
            element = self.driver.find_element(By.ID, element_id)

        if element_class is not None:
            element = self.driver.find_element(By.ID, element_id)

        if element is not None:
            try:
                element.click()
            except:
                logger.info('Consent button not found')


    def _test_scroll_page(self, xpath=None, css_selector=None):
        if css_selector:
            selector = """const mainWrapper = document.querySelector('{condition}')"""
            selector = selector.format(condition=css_selector)
        else:
            selector = """const element = document.evaluate("{condition}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)"""
            selector = selector.format(condition=xpath)

        body = """
        const elementToScroll = mainWrapper.querySelector('div[tabindex="-1"]')

        const elementHeight = elementToScroll.scrollHeight
        let currentPosition = elementToScroll.scrollTop

        // Indicates the scrolling speed
        const scrollStep = Math.ceil(elementHeight / {scroll_step})

        currentPosition += scrollStep
        elementToScroll.scroll(0, currentPosition)

        return [ currentPosition, elementHeight ]
        """.format(scroll_step=self.default_scroll_step)

        script = css_selector + '\n' + body
        return script


class CrawlerMixin(ActionsMixin, SEOMixin, EmailMixin):
    urls_to_visit = set()
    visited_urls = set()
    webdriver = Chrome
    debug_mode = False
    # webdriver = Edge

    def __init__(self):
        self._start_url_object = None

        path = os.environ.get('KRYPTONE_WEBDRIVER', None)
        if path is None:
            logger.error('Could not find web driver')
        else:
            # options = EdgeOptions()
            options = ChromeOptions()
            options.add_argument('--remote-allow-origins=*')
            options.add_argument(f'user-agent={RANDOM_USER_AGENT()}')
            # options.add_argument(f"--proxy-server={}")

            self.driver = self.webdriver(
                executable_path=path,
                options=options
            )

            # post_init.send(self)

            db_signal.connect(backends.airtable_backend, sender=self)
            db_signal.connect(backends.notion_backend, sender=self)
            db_signal.connect(backends.google_sheets_backend, sender=self)

    # def __del__(self):
    #     # When the program terminates,
    #     # always back up the urls that
    #     # were visited or unvisited
    #     self._backup_urls()
    #     logger.info('Crawl finished')

    @property
    def get_html_page_content(self):
        """Returns HTML elements of the
        current page"""
        return self.driver.page_source

    @property
    def get_page_link_elements(self):
        """Returns all the selenium `<a></a>` anchor tags
        of the current page"""
        return self.driver.find_elements(By.TAG_NAME, 'a')

    @property
    def completion_percentage(self):
        """Indicates the level of completion
        for the current crawl session"""
        result = len(self.visited_urls) / len(self.urls_to_visit)
        return round(result, 0)
    
    @property
    def name(self):
        return 'crawler'
    
    def create_dump(self):
        """Dumps the collected results to a file.
        This functions is called only when an exception
        occurs during the crawling process
        """
        
    
    def _backup_urls(self):
        """Backs up the urls both in the memory
        cache, and in the cache file"""
        urls_data = {
            'urls_to_visit': list(self.urls_to_visit),
            'visited_urls': list(self.visited_urls)
        }
        cache.set_value('urls_data', urls_data)

        write_json_document('cache.json', urls_data)


class BaseCrawler(CrawlerMixin):
    start_url = None
    url_validators = []
    url_filters = []

    def get_filename(self, length=5, extension=None):
        characters = string.ascii_lowercase + string.digits
        name = ''.join(random.choice(characters) for _ in range(length))
        if extension is not None:
            return f'{name}.{extension}'
        return name

    def build_headers(self, options):
        headers = {
            'User-Agent': RANDOM_USER_AGENT(),
            'Accept-Language': 'en-US,en;q=0.9'
        }
        items = [f"--header={key}={value})" for key, value in headers.items()]
        options.add_argument(' '.join(items))

    def run_filters(self, exclude=True):
        """Filters out or in urls included in the list 
        of urls to visit. The default action is to 
        exclude all urls that meet sepcific conditions"""
        if self.url_filters:
            urls_to_filter = []
            for instance in self.url_filters:
                if not urls_to_filter:
                    urls_to_filter = list(filter(instance, self.urls_to_visit))
                else:
                    urls_to_filter = list(filter(instance, urls_to_filter))

            message = f"Url filter completed."
            logger.info(message)
            return urls_to_filter
        # Ensure that we return the original
        # urls to visit if there are no filters
        # or this might return nothing
        return self.urls_to_visit

    def get_page_urls(self, same_domain=True):
        """Returns all the urls present on the
        actual given page"""
        elements = self.get_page_link_elements
        for element in elements:
            link = element.get_attribute('href')

            # Turn the url into a Python object
            # to make more usable for us
            link_object = urlparse(link)

            # 1. We do not want to add an item
            # to the list if it already exists,
            # if its invalid or None
            if link in self.urls_to_visit:
                continue

            if link in self.visited_urls:
                continue

            if link is None or link == '':
                continue

            # Links such as http://exampe.com/path#
            # are useless and can create
            # useless repetition
            if link.endswith('#'):
                continue

            # If the link is similar to the originally
            # visited url, skip it - This is a security measure
            if link_object.netloc != self._start_url_object.netloc:
                continue

            # If the url contains a fragment, it is the same
            # as visiting the root page for instance:
            # example.com/#google is the same as example.com/
            if link_object.fragment:
                continue

            # If we have already visited the home page then
            # skip all urls that include the '/' path - This
            # is another security measure
            if link_object.path == '/' and self._start_url_object.path == '/':
                continue

            # Reconstruct a partial urls for example
            # /google becomes https://example.com/google
            if link_object.path != '/' and link.startswith('/'):
                link = f'{self._start_url_object.scheme}://{self._start_url_object.netloc}{link}'

            self.urls_to_visit.add(link)

        # Finally, run all the filters to exclude
        # urls that the user does not want to visit
        self.urls_to_visit = set(self.run_filters())

        logger.info(f"Found {len(elements)} urls")

    def post_visit_actions(self, **kwargs):
        """Actions to run on the page just after
        the crawler has visited a page e.g. clicking
        on cookie button banner"""
        pass

    def run_actions(self, current_url, **kwargs):
        """Additional custom actions to execute on the page
        once all the default steps are completed"""
        pass

    def resume(self, **kwargs):
        """From a previous list of urls to visit 
        and visited urls, resume the previous
        scraping session"""
        data = read_json_document('cache.json')
        self.urls_to_visit = set(data['urls_to_visit'])
        self.visited_urls = set(data['visited_urls'])
        self.start(**kwargs)

    def start_from_sitemap_xml(self, url, **kwargs):
        """Start a new crawling session starting
        from the sitemap of a given website"""
        if not url.endswith('.xml'):
            raise ValueError('Url should point to a sitemap')

        response = requests.get(url)
        parser = etree.XMLParser(encoding='utf-8')
        xml = etree.fromstring(response.content, parser)
        self.start(start_urls=[], **kwargs)

    def start_from_html_sitemap(self, url, **kwargs):
        """Start crawling from the sitemap page section
        of a given website"""
        if not 'sitemap' in url:
            raise ValueError('Url should be the sitemap page')
        
        body = self.driver.find_element(By.TAG_NAME, 'body')
        link_elements = body.find_elements(By.TAG_NAME, 'a')

        urls = []
        for element in link_elements:
            urls.append(element.get_attribute('href'))
        self.start(start_urls=urls, **kwargs)

    def start(self, start_urls=[], debug_mode=False, wait_time=25, run_audit=False, language='en'):
        """Entrypoint to start the web scrapper"""
        self.debug_mode = debug_mode

        if self.debug_mode:
            logger.info('Starting Kryptone in debug mode...')
        else:
            logger.info('Starting Kryptone...')

        if self.start_url is not None:
            self.urls_to_visit.add(self.start_url)
            self._start_url_object = urlparse(self.start_url)

        if start_urls:
            self.urls_to_visit.update(set(start_urls))

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url is None:
                continue

            # In the case where the user has provided a
            # set of urls directly in the function,
            # start_url would be None
            if self.start_url is None:
                self.start_url = current_url
                self._start_url_object = urlparse(self.start_url)

            current_url_object = urlparse(current_url)
            # If we are not on the same domain as the
            # starting url: *stop*. we are not interested
            # in exploring the whole internet
            if current_url_object.netloc != self._start_url_object.netloc:
                continue
            
            logger.info(f'Going to url: {current_url}')
            self.driver.get(current_url)
            # navigation.send(self, current_url=current_url)
            # Always wait for the body section of
            # the page to be located  or visible
            wait = WebDriverWait(self.driver, 8)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            self.post_visit_actions(current_url=current_url)

            self.visited_urls.add(current_url)

            # We can either crawl all the website
            # or just specific page
            self.get_page_urls()

            self._backup_urls()

            if run_audit:
                # Audit the website TODO: Improve the way in
                # in which the text is extracted from the page
                self.audit_page(current_url, language=language)
                write_json_document('audit.json', self.page_audits)

                vocabulary = self.global_audit(language=language)
                write_json_document('global_audit.json', vocabulary)

                cache.set_value('page_audit', self.page_audits)
                cache.set_value('global_audit', vocabulary)

                logger.info('Audit complete...')

            self.emails(
                self.get_transformed_raw_page_text,
                elements=self.get_page_link_elements
            )
            # Format each email as [[...], ...] in order to comply
            # with the way that the csv writer outputs the rows
            emails = list(map(lambda x: [x], self.emails_container))
            write_csv_document('emails.csv', emails)
            db_signal.send(
                self,
                emails=self.emails_container
            )

            # Run custom user actions once 
            # everything is completed
            self.run_actions(current_url)

            logger.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)


class SinglePageAutomater(CrawlerMixin):
    """Automates user defined actions on a
    single or multiple user provided 
    pages as oppposed to crawing the
    whole website"""
    
    start_urls = []

    @property
    def name(self):
        return 'automation'

    def start(self, start_urls=[], wait_time=None, debug_mode=False):
        """Entrypoint to start the web scrapper"""
        self.debug_mode = debug_mode

        logger.info('Starting Kryptone automation...')

        if isinstance(self.start_urls, URLFile):
            self.start_urls = list(self.start_urls)

        self.start_urls.extend(start_urls)
        start_urls = self.start_urls

        if start_urls:
            self.urls_to_visit.update(set(start_urls))

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url is None:
                continue

            logger.info(f'Going to url: {current_url}')
            self.driver.get(current_url)
            # navigation.send(self, current_url=current_url)
            # Always wait for the body section of
            # the page to be located  or visible
            wait = WebDriverWait(self.driver, 8)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            self.post_visit_actions(current_url=current_url)

            self.visited_urls.add(current_url)

            self._backup_urls()

            self.emails(
                self.get_transformed_raw_page_text,
                elements=self.get_page_link_elements
            )
            write_csv_document('emails.csv', self.emails_container)

            # Run custom user actions once
            # everything is completed
            self.run_actions(current_url)
            db_signal.send(
                self,
                current_url=current_url,
                emails=self.emails_container
            )

            logger.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)
