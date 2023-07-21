import json
import random
import re
import string
import time
from collections import defaultdict
from urllib.parse import urlparse

import requests
from lxml import etree
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import logger
from kryptone.cache import Cache
from kryptone.conf import settings
from kryptone.db import backends
from kryptone.db.connections import redis_connection
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.signals import Signal
from kryptone.utils.file_readers import (read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.iterators import JPEGImagesIterator
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URLFile

# post_init = Signal()
navigation = Signal()
db_signal = Signal()

cache = Cache()

WEBDRIVER_ENVIRONMENT_PATH = 'KRYPTONE_WEBDRIVER'


def collect_images_receiver(sender, current_url=None, **kwargs):
    """Collects every images present on the
    actual webpage and classifies them"""
    try:
        image_elements = sender.driver.find_elements(By.TAG_NAME, 'img')
    except:
        pass
    else:
        instance = JPEGImagesIterator(current_url, image_elements)
        logger.info(f'Collected {len(instance)} images')
    finally:
        cache.extend_list('images', instance.urls)


def get_selenium_browser_instance(browser_name=None):
    """Creates a new selenium browser instance"""
    browser_name = browser_name or settings.WEBDRIVER
    browser = Chrome if browser_name == 'Chrome' else Edge
    manager_instance = ChromeDriverManager if browser_name == 'Chrome' else EdgeChromiumDriverManager

    options_klass = ChromeOptions if browser_name == 'Chrome' else EdgeOptions
    options = options_klass()
    options.add_argument('--remote-allow-origins=*')
    options.add_argument(f'user-agent={RANDOM_USER_AGENT()}')

    service = Service(manager_instance().install())
    return browser(service=service, options=options)


class ActionsMixin:
    # Default speed at which the robot
    # should scroll a given page
    default_scroll_step = 80

    def scroll_window(self, wait_time=5, increment=1000, stop_at=None):
        """Scrolls the entire window by incremeting the current
        scroll position by a given number of pixels"""
        can_scroll = True
        new_scroll_pixels = 1000

        while can_scroll:
            scroll_script = f"""window.scroll(0, {new_scroll_pixels})"""

            self.driver.execute_script(scroll_script)
            # Scrolls until we get a result that determines that we
            # have actually scrolled to the bottom of the page
            has_reached_bottom = self.driver.execute_script(
                """return (window.innerHeight + window.scrollY) >= (document.documentElement.scrollHeight - 100)"""
            )
            if has_reached_bottom:
                can_scroll = False

            current_position = self.driver.execute_script(
                """return window.scrollY""")
            if stop_at is not None and current_position > stop_at:
                can_scroll = False

            new_scroll_pixels = new_scroll_pixels + increment
            time.sleep(wait_time)

    def save_to_local_storage(self, name, data):
        """Saves datat to the browsers local storage
        for the current automation session"""
        data = json.dumps(data)
        script = f"""
        localStorage.setItem('{name}', JSON.stringify({data}))
        """
        self.driver.execute_script(script)

    def click_consent_button(self, element_id=None, element_class=None):
        """Click the consent to cookies button which often
        tends to appear on websites"""
        try:
            element = None
            if element_id is not None:
                element = self.driver.find_element(By.ID, element_id)

            if element_class is not None:
                element = self.driver.find_element(By.CLASS_NAME, element_id)
            element.click()
        except:
            logger.info('Consent button not found')

    def evaluate_xpath(self, path):
        return self.driver.execute_script(
            f"""
            const result = document.evaluate({path}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
            return result.singleNodeValue
            """
        )

    # TODO:
    # def scroll_page(self, wait_time=8):
    #     can_scroll = True

    #     scroll_script = """
    #     const elementHeight = document.body.scrollHeight
    #     let currentPosition = window.scrollY

    #     // Indicates the scrolling speed
    #     const scrollStep = Math.ceil(elementHeight / {scroll_step})

    #     currentPosition += scrollStep
    #     window.scroll(0, currentPosition)

    #     return [ currentPosition, elementHeight ]
    #     """
    #     scroll_script = scroll_script.format(
    #         scroll_step=self.default_scroll_step
    #     )

    #     max_tries = 10
    #     bottom_of_page_tries = 0
    #     scroll_height_tries = 0
    #     previous_position = 0
    #     previous_scroll_height = 0

    #     while can_scroll:
    #         current_position, scroll_height = self.driver.execute_script(scroll_script)

    #         # If we have reached the bottom of the page, try to
    #         # scroll for a maximum amount of tries before stopping
    #         # in order to ensure all data was loaded
    #         if previous_position > 0 and current_position >= scroll_height:
    #             bottom_of_page_tries = bottom_of_page_tries + 1

    #             if bottom_of_page_tries > max_tries:
    #                 can_scroll = False

    #         # FIXME: There are cases when the curent_position > scroll_height
    #         # but there's still more content to be loaded which means that
    #         # technically, the document height isn't always equal to the
    #         # to the current position and my never reach it.
    #         # Sleep in order to allow page to refresh correctly and evenually
    #         # get more data to load
    #         if previous_scroll_height > 0 and scroll_height == previous_scroll_height:
    #             scroll_height_tries = scroll_height_tries + 1

    #             # If we were able to refresh the new document
    #             # height keep scrolling
    #             if scroll_height != previous_scroll_height:
    #                 scroll_height_tries = 0
    #                 bottom_of_page_tries = 0
    #                 time.sleep(2)

    #             if scroll_height_tries > max_tries:
    #                 can_scroll = False

    #         # Trigger when the scroll position is equal
    #         # to the total scrollable size of the page
    #         if current_position == scroll_height:
    #             can_scroll = False

    #         previous_position = current_position
    #         previous_scroll_height = scroll_height

    #         # Sleep a couple of seconds because sometimes
    #         # webpages will load content once we hit a given
    #         # scroll position
    #         time.sleep(wait_time)
    #         print('scrolling', current_position, scroll_height,
    #               'bottom_of_page_tries', bottom_of_page_tries, 'scroll_height_tries', scroll_height_tries)

    def _test_scroll_page(self, xpath=None, css_selector=None):
        """Scrolls a specific portion on the page"""
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
    browser_name = None
    debug_mode = False

    def __init__(self):
        self._start_url_object = None
        self.driver = get_selenium_browser_instance(
            browser_name=self.browser_name)

        navigation.connect(collect_images_receiver, sender=self)

        db_signal.connect(backends.airtable_backend, sender=self)
        db_signal.connect(backends.notion_backend, sender=self)
        db_signal.connect(backends.google_sheets_backend, sender=self)

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

    def _backup_urls(self):
        """Backs up the urls both in memory
        cache and file cache"""
        urls_data = {
            'urls_to_visit': list(self.urls_to_visit),
            'visited_urls': list(self.visited_urls)
        }
        cache.set_value('urls_data', urls_data)

        write_json_document(
            f'{settings.CACHE_FILE_NAME}.json',
            urls_data
        )
        db_signal.send(
            self,
            data_type='urls',
            urls_data=urls_data
        )

    def post_visit_actions(self, **kwargs):
        """Actions to run on the page just after
        the crawler has visited a page e.g. clicking
        on cookie button banner"""
        pass

    def run_actions(self, current_url, **kwargs):
        """Additional custom actions to execute on the page
        once all the default steps are completed"""
        pass

    def create_dump(self):
        """Dumps the collected results to a file.
        This functions is called only when an exception
        occurs during the crawling process
        """


class BaseCrawler(CrawlerMixin):
    start_url = None
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

    def resume(self, **kwargs):
        """From a previous list of urls to visit 
        and visited urls, resume the previous
        scraping session. We check Redis as the
        primary database if there is connection,
        then PyMemcache and finally the file cache
        as a finale resort"""
        redis = redis_connection()
        if redis:
            data = redis.get('cache')
        else:
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

    def start(self, start_urls=[], debug_mode=False, wait_time=None, run_audit=False, language=None):
        """Entrypoint to start the web scrapper"""
        self.debug_mode = debug_mode

        wait_time = wait_time or settings.WAIT_TIME

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

            # Always wait for the body section of
            # the page to be located  or visible
            wait = WebDriverWait(self.driver, 8)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            self.post_visit_actions(current_url=current_url)

            # Post navigation signal
            # TEST: This has to be tested
            navigation.send(
                self,
                current_url=current_url,
                images_list_filter=['jpg', 'jpeg', 'webp']
            )

            self.visited_urls.add(current_url)

            # We can either crawl all the website
            # or just specific page
            self.get_page_urls()
            self._backup_urls()

            if run_audit:
                language = language or settings.WEBSITE_LANGUAGE
                self.audit_page(current_url, language=language)
                write_json_document('audit.json', self.page_audits)

                vocabulary = self.global_audit(language=language)
                write_json_document('global_audit.json', vocabulary)

                cache.set_value('page_audit', self.page_audits)
                cache.set_value('global_audit', vocabulary)
                db_signal.send(
                    self,
                    page_audit=self.page_audits,
                    global_audit=vocabulary
                )

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

            # Always wait for the body section of
            # the page to be located  or visible
            wait = WebDriverWait(self.driver, 8)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            self.post_visit_actions(current_url=current_url)

            # Post navigation signal
            # TEST: This has to be tested
            navigation.send(self, current_url=current_url)

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
            time.sleep(wait_time or 15)
