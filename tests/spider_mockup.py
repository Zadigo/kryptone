import datetime
import json
import random
import re
import string
import time
from collections import defaultdict, namedtuple
from urllib.parse import unquote, urlparse, urlunparse

import pytz
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
# from kryptone.cache import Cache
from kryptone.conf import settings
from kryptone.db import backends
from kryptone.db.connections import memcache_connection, redis_connection
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.signals import Signal
from kryptone.utils.file_readers import (read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.iterators import JPEGImagesIterator
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL, URLFile

DEFAULT_META_OPTIONS = {
    'domains', 'audit_page', 'url_passes_tests',
    'debug_mode', 'site_language'
}


class CrawlerOptions:
    def __init__(self, spider, name):
        self.spider = spider
        self.spider_name = name.lower()
        self.verbose_name = name.title()
        self.initial_spider_meta = None

    def __repr__(self):
        return f'<{self.__class__.__name__} for {self.verbose_name}>'

    def add_meta_options(self, options):
        for name, value in options:
            if name not in DEFAULT_META_OPTIONS:
                raise ValueError(
                    "Meta for model '{name}' received "
                    "and illegal option '{option}'".format(
                        name=self.verbose_name,
                        option=name
                    )
                )
            setattr(self, name, value)

    def prepare(self):
        for option in DEFAULT_META_OPTIONS:
            if not hasattr(self, option):
                if option in ['domains', 'url_passes_tests']:
                    setattr(self, option, [])

                if option in ['audit_page', 'debug_mode', 'debug_mode']:
                    setattr(self, option, False)

                if option == 'site_language':
                    setattr(self, option, None)


class Crawler(type):
    def __new__(cls, name, bases, attrs):
        super_new = super().__new__

        parents = [b for b in bases if isinstance(b, Crawler)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, attrs)

        if name == 'SiteCrawler':
            return new_class

        meta_attributes = attrs.pop('Meta', None)
        meta = CrawlerOptions(new_class, name)
        meta.initial_spider_meta = meta_attributes
        setattr(new_class, '_meta', meta)

        if meta_attributes is not None:
            meta_dict = meta_attributes.__dict__

            declared_options = []
            for key, value in meta_dict.items():
                if key.startswith('__'):
                    continue
                declared_options.append((key, value))
            meta.add_meta_options(declared_options)

        new_class.prepare()
        return new_class

    def prepare(cls):
        cls._meta.prepare()


class BaseCrawler(metaclass=Crawler):
    urls_to_visit = set()
    visited_urls = set()
    browser_name = None
    debug_mode = False
    timezone = 'UTC'
    default_scroll_step = 80

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

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
        return 'site_crawler'

    @property
    def get_html_page_content(self):
        """Returns HTML elements of the
        current page"""
        return self.driver.page_source

    @property
    def get_page_link_elements(self):
        """Returns all the selenium `<a></a>` anchor tags
        of the current page"""
        # return self.driver.find_elements(By.TAG_NAME, 'a')
        return ['http://example.com/about.html', 'http://example.com/google']

    def _backup_urls(self):
        """Backs up the urls both in memory
        cache and file cache"""
        d = self.get_current_date()

        urls_data = {
            'spider': self.__class__.__name__,
            'timestamp': d.strftime('%Y-%M-%d %H:%M:%S'),
            'urls_to_visit': list(self.urls_to_visit),
            'visited_urls': list(self.visited_urls)
        }
        # cache.set_value('urls_data', urls_data)

        write_json_document(
            f'{settings.CACHE_FILE_NAME}.json',
            urls_data
        )
        # db_signal.send(
        #     self,
        #     data_type='urls',
        #     urls_data=urls_data
        # )

    def run_filters(self):
        """Excludes urls in the list of urls to visit based
        on the return value of the function in `url_filters`
        """
        if self._meta.url_passes_tests:
            results = defaultdict(list)
            for url in self.urls_to_visit:
                truth_array = results[url]
                for instance in self._meta.url_passes_tests:
                    truth_array.append(instance(url))

            filtered_urls = []
            for url, truth_array in results.items():
                if not all(truth_array):
                    continue
                filtered_urls.append(url)
            message = f"Url filter completed"
            logger.info(message)
            return filtered_urls
        # Ensure that we return the original
        # urls to visit if there are no filters
        # or this might return nothing
        return self.urls_to_visit

    def add_urls(self, *urls_or_paths):
        """Manually add urls to the current urls to
        visit. This is useful for cases where urls are
        nested in other elements than links and that
        cannot actually be retrieved by the spider"""
        for item in urls_or_paths:
            new_url = str(item)
            if item.startswith('/'):
                new_url = urlunparse((
                    self._start_url_object.scheme,
                    self._start_url_object.netloc,
                    item,
                    None,
                    None,
                    None
                ))

            if new_url in self.visited_urls:
                continue

            if new_url in self.urls_to_visit:
                continue

            self.urls_to_visit.add(new_url)

    def get_page_urls(self, same_domain=True):
        """Returns all the urls present on the
        actual given page"""
        elements = self.get_page_link_elements
        logger.info(f"Found {len(elements)} urls")

        for element in elements:
            # link = element.get_attribute('href')
            link = element

            # Turn the url into a Python object
            # to make it more usable for us
            link_object = urlparse(link)

            # We do not want to add an item
            # to the list if it already exists,
            # if it is invalid or None
            if link in self.urls_to_visit:
                continue

            if link in self.visited_urls:
                continue

            if link is None or link == '':
                continue

            # Links such as http://exampe.com/path#
            # are useless and can create
            # useless repetition for us
            if link.endswith('#'):
                continue

            # If the link is similar to the initially
            # visited url, skip it. NOTE: This is essentially
            # a  security measure
            if link_object.netloc != self._start_url_object.netloc:
                continue

            # If the url contains a fragment, it is the same
            # as visiting the root page, for example:
            # example.com/#google is the same as example.com/
            if link_object.fragment:
                continue

            # If we have already visited the home page then
            # skip all urls that include the '/' path.
            # NOTE: This is another security measure
            if link_object.path == '/' and self._start_url_object.path == '/':
                continue

            # Reconstruct a partial url for example
            # /google becomes https://example.com/google
            if link_object.path != '/' and link.startswith('/'):
                link = f'{self._start_url_object.scheme}://{self._start_url_object.netloc}{link}'
                # link = urlunparse((
                #     self._start_url_object.scheme,
                #     self._start_url_object.netloc,
                #     link,
                #     None,
                #     None,
                #     None,
                #     None
                # ))

            self.urls_to_visit.add(link)

        # Finally, run all the filters to exclude
        # urls that the user does not want to visit
        # from the list of urls. NOTE: This re-initializes
        # the list of urls to visit
        # previous_state = self.urls_to_visit.copy()
        self.urls_to_visit = set(self.run_filters())
        # excluded_urls = previous_state.difference(self.urls_to_visit)
        # logger.info(f'Ignored {len(excluded_urls)} urls')

    def calculate_performance(self):
        """Returns the amount of time for which the
        spider has been running"""
        self._end_date = self.get_current_date()
        days = (self._start_date - self._end_date).days
        completed_time = round(time.time() - self._start_time, 1)
        days = 0 if days < 0 else days
        return self.performance_audit(days, completed_time)

    def get_current_date(self):
        timezone = pytz.timezone(self.timezone)
        return datetime.datetime.now(tz=timezone)

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


class SiteCrawler(SEOMixin, EmailMixin, BaseCrawler):
    start_url = None
    start_xml_url = None

    def __init__(self, browser_name=None):
        self._start_url_object = None
        # self.driver = get_selenium_browser_instance(
        #     browser_name=browser_name or self.browser_name
        # )

        # navigation.connect(collect_images_receiver, sender=self)

        # db_signal.connect(backends.airtable_backend, sender=self)
        # db_signal.connect(backends.notion_backend, sender=self)
        # db_signal.connect(backends.google_sheets_backend, sender=self)

        self._start_date = self.get_current_date()
        self._end_date = None

        self._start_time = time.time()
        self._end_time = None
        self.performance_audit = namedtuple(
            'Performance', ['days', 'duration']
        )

    def start(self, start_urls=[], url_cache=None, **kwargs):
        """Entrypoint to start the spider

        >>> instance = BaseCrawler()
        ... instance.start(start_urls=["http://example.com"])
        """
        # To ensure efficient navigation and/or
        # scrapping, use a maximised window since
        # layouts can fundamentally change when
        # using a smaller window
        logger.info(f'{self.__class__.__name__} ready to crawl website')
        # self.driver.maximize_window()

        wait_time = settings.WAIT_TIME

        if self._meta.debug_mode:
            logger.info('Starting Kryptone in debug mode...')
        else:
            logger.info('Starting Kryptone...')

        if url_cache is not None:
            self.urls_to_visit = url_cache.urls_to_visit
            self.visited_urls = url_cache.visited_urls

        if self.start_xml_url is not None:
            start_urls = self.start_from_sitemap_xml(self.start_xml_url)
        elif self.start_url is not None:
            # self.urls_to_visit.add(self.start_url)
            self.add_urls(self.start_url)
            self._start_url_object = urlparse(self.start_url)

        if start_urls:
            self.add_urls(*start_urls)

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
            # self.driver.get(current_url)

            # Always wait for the body section of
            # the page to be located  or visible
            # wait = WebDriverWait(self.driver, 8)
            # wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            # self.post_visit_actions(current_url=current_url)

            # Post navigation signal
            # TEST: This has to be tested
            # navigation.send(
            #     self,
            #     current_url=current_url,
            #     images_list_filter=['jpg', 'jpeg', 'webp']
            # )

            self.visited_urls.add(current_url)

            # We can either crawl all the website
            # or just specific page
            self.get_page_urls()
            self._backup_urls()

            if self._meta.audit_page:
                self.audit_page(current_url)
                write_json_document('audit.json', self.page_audits)

                vocabulary = self.global_audit(
                    language=self._meta.site_language)
                write_json_document('global_audit.json', vocabulary)

                # cache.set_value('page_audit', self.page_audits)
                # cache.set_value('global_audit', vocabulary)
                # db_signal.send(
                #     self,
                #     page_audit=self.page_audits,
                #     global_audit=vocabulary
                # )

                logger.info('Audit complete...')

            self.emails(
                self.get_transformed_raw_page_text,
                elements=self.get_page_link_elements
            )
            # Format each email as [[...], ...] in order to comply
            # with the way that the csv writer outputs the rows
            emails = list(map(lambda x: [x], self.emails_container))
            write_csv_document('emails.csv', emails)
            # db_signal.send(
            #     self,
            #     emails=self.emails_container
            # )

            # Run custom user actions once
            # everything is completed
            url_instance = URL(current_url)
            self.run_actions(current_url, url_object=url_instance)

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            logger.info(f"Waiting {wait_time}s")
            time.sleep(wait_time)
from kryptone.utils.urls import URLPassesTest

class TalentView(SiteCrawler):
    class Meta:
        url_passes_tests = [
            URLPassesTest('/google')
        ]


t = TalentView()
t.start_url = 'http://example.com'
t.start()
