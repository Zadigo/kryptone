import asyncio
import bisect
import dataclasses
import datetime
import inspect
import os
import random
import socket
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from importlib import import_module
from urllib.parse import unquote, urlencode, urljoin, urlunparse
from urllib.robotparser import RobotFileParser
from uuid import uuid4

import pandas
import pytz
import requests
from asgiref.sync import sync_to_async
from lxml import etree
from requests import Session
from requests.models import Request
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import constants, exceptions, logger, receivers, signal_constants
from kryptone.conf import settings
from kryptone.storages import BaseStorage, FileStorage
from kryptone.utils import file_readers
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.iterators import AsyncIterator
from kryptone.utils.module_loaders import import_from_module
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL
from kryptone.webhooks import Webhooks

DEFAULT_META_OPTIONS = {
    'domains', 'url_ignore_tests', 'url_rule_tests',
    'debug_mode', 'default_scroll_step',
    'router', 'crawl', 'start_urls',
    'ignore_queries', 'ignore_images', 'restrict_search_to',
    'url_gather_ignore_tests', 'database'
}


def get_selenium_browser_instance(browser_name=None, headless=False, load_images=True, load_js=True):
    """Creates a new selenium browser instance

    >>> browser = get_selenium_browser_instance()
    ... browser.get('...')
    ... browser.quit()
    """
    browser_name = browser_name or settings.WEBDRIVER
    browser = Chrome if browser_name == 'Chrome' else Edge
    manager_instance = ChromeDriverManager if browser_name == 'Chrome' else EdgeChromiumDriverManager

    options_klass = ChromeOptions if browser_name == 'Chrome' else EdgeOptions
    options = options_klass()
    options.add_argument('--remote-allow-origins=*')
    options.add_argument(f'--user-agent={RANDOM_USER_AGENT()}')
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # Allow Selenium to be launched
    # in headless mode
    if headless:
        options.headless = True

    # 0 = Default, 1 = Allow, 2 = Block
    preferences = {
        'profile.default_content_setting_values': {
            'images': 0 if load_images else 2,
            'javascript': 0 if load_js else 2,
            'popups': 2,
            'geolocation': 2,
            'notifications': 2
        }
    }
    options.add_experimental_option('prefs', preferences)

    # Proxies
    if settings.PROXY_IP_ADDRESS is not None:
        proxy = Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        proxy.http_proxy = settings.PROXY_IP_ADDRESS
        options.add_argument(
            f'--proxy-server=http://{settings.PROXY_IP_ADDRESS}'
        )
        options.add_argument('--disable-gpu')

    service = Service(manager_instance().install())
    return browser(service=service, options=options)


class CrawlerOptions:
    """Stores the main options for the crawler"""

    def __init__(self, spider, name):
        self.spider = spider
        self.spider_name = name.lower()
        self.verbose_name = name.title()
        self.initial_spider_meta = None

        self.domains = []
        self.url_ignore_tests = []
        self.debug_mode = False
        self.default_scroll_step = 80
        self.router = None
        self.crawl = True
        self.start_urls = []
        # Restrict url retrieval only to
        # to specific sections of the page
        # e.g. body, div[class="example"]
        self.restrict_search_to = []
        # Ignore urls with query strings
        self.ignore_queries = False
        self.ignore_images = False
        self.url_gather_ignore_tests = []
        self.url_rule_tests = []

    def __repr__(self):
        return f'<{self.__class__.__name__} for {self.verbose_name}>'

    @property
    def has_start_urls(self):
        return len(self.start_urls) > 0

    def add_meta_options(self, options):
        for name, value in options:
            if name not in DEFAULT_META_OPTIONS:
                raise ValueError(
                    f"Meta for model '{self.verbose_name}' received "
                    f"an illegal option '{name}'"
                )
            setattr(self, name, value)

    def prepare(self):
        # The user can either use a list of generators or directly
        # use a generator (URLGenerator, PagePaginationGenerator)
        # or other types of generators launch the spider
        if hasattr(self.start_urls, 'resolve_generator'):
            self.start_urls = list(self.start_urls)
        elif isinstance(self.start_urls, list):
            start_urls = []
            for item in self.start_urls:
                if hasattr(item, 'resolve_generator'):
                    start_urls.extend(list(item))
                    continue

                if isinstance(item, str):
                    start_urls.extend([item])
                    continue

            self.start_urls = start_urls


@dataclass
class Performance:
    iteration_count: int = 0
    start_date: datetime.datetime = field(
        default_factory=datetime.datetime.now
    )
    end_date: datetime.datetime = field(
        default_factory=datetime.datetime.now
    )
    timezone: str = 'UTC'
    error_count: int = 0
    duration: int = 0

    def __post_init__(self):
        # Since the end date is aware, we need to set
        # the timezone on the start date
        self.timezone = pytz.timezone(self.timezone)
        self.start_date.replace(tzinfo=self.timezone)

    def calculate_duration(self):
        self.duration = (self.start_date - self.end_date)

    def add_error_count(self):
        self.error_count = self.error_count + 1

    def add_iteration_count(self):
        self.iteration_count = self.iteration_count + 1

    def json(self):
        container = OrderedDict()
        for field in dataclasses.fields(self):
            container[field.name] = getattr(self, field.name)
        return container


class Crawler(type):
    def __new__(cls, name, bases, attrs):
        super_new = super().__new__

        parents = [b for b in bases if isinstance(b, Crawler)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, attrs)
        # if name == 'SiteCrawler':
        #     return new_class

        meta_object = attrs.pop('Meta', None)
        meta = CrawlerOptions(new_class, name)
        meta.initial_spider_meta = meta_object
        setattr(new_class, '_meta', meta)

        if meta_object is not None:
            meta_object_dict = meta_object.__dict__

            declared_options = []
            for key, value in meta_object_dict.items():
                if key.startswith('__'):
                    continue

                declared_options.append((key, value))
            meta.add_meta_options(declared_options)

        new_class.prepare()
        return new_class

    def prepare(cls):
        cls._meta.prepare()


class BaseCrawler(metaclass=Crawler):
    DATA_CONTAINER = []
    model = None

    urls_to_visit = set()
    visited_urls = set()
    visited_pages_count = 0
    list_of_seen_urls = set()
    browser_name = None
    timezone = 'UTC'
    default_scroll_step = 80

    storage = None
    additional_storages = []

    def __init__(self, browser_name=None):
        self.start_url = None
        self.url_distribution = defaultdict(list)
        self.spider_uuid = uuid4()

        if not self._meta.debug_mode:
            self.driver = get_selenium_browser_instance(
                browser_name=browser_name or self.browser_name,
                headless=settings.HEADLESS,
                load_images=settings.LOAD_IMAGES,
                load_js=settings.LOAD_JS
            )

    def __repr__(self):
        klass_name = self.__class__.__name__
        return f'<{klass_name}: {self.spider_uuid}>'

    def __hash__(self):
        return hash((self.spider_uuid))

    @property
    def get_page_title(self):
        element = self.driver.find_element(By.TAG_NAME, 'title')
        return element.text

    @property
    def get_current_date(self):
        timezone = pytz.timezone(self.timezone)
        return datetime.datetime.now(tz=timezone)

    @property
    def get_origin(self):
        if self.start_url is None:
            return ''

        return urlunparse((
            self.start_url.url_object.scheme,
            self.start_url.url_object.netloc,
            None,
            None,
            None,
            None
        ))

    @cached_property
    def calculate_completion_percentage(self):
        return len(self.visited_urls) / len(self.urls_to_visit)

    def collect_page_urls(self):
        """Returns all the links present on the
        currently visited page"""
        found_urls = []
        # Restrict the url collection to specific
        # section the page -; by default gets all
        # the urls on the page
        if self._meta.restrict_search_to:
            for selector in self._meta.restrict_search_to:
                script = f"""
                const urls = Array.from(document.querySelectorAll('{selector} a'))
                return urls.map(x => x.href)
                """
                urls = self.driver.execute_script(script)

                if urls:
                    logger.info(
                        f"Found {len(urls)} url(s) "
                        f"in page section: '{selector}'"
                    )
                found_urls.extend(urls)
        else:
            found_urls = self.driver.execute_script(
                """
                const urls = Array.from(document.querySelectorAll('a'))
                return urls.map(x => x.href)
                """
            )
        return found_urls

    def save_object(self, data, check_fields_null=[]):
        """Saves a new object in the container"""
        if self.model is None:
            raise ValueError(
                "You need to implement a dataclass model "
                "on the spider when trying to use save"
            )

        if not dataclasses.is_dataclass(self.model):
            raise ValueError(
                "Your model should be an instance of "
                "of a dataclass"
            )

        if isinstance(data, dict):
            data = [data]

        instance_fields = dataclasses.fields(self.model)
        instances = map(lambda x: self.model(**x), data)

        for instance in instances:
            for field in instance_fields:
                func_name = f'clean_{field.name}'
                if hasattr(instance, func_name):
                    result = getattr(instance, func_name)(
                        getattr(instance, field.name))
                    setattr(instance, field.name, result)

            for check_field in check_fields_null:
                if getattr(instance, check_field) is None:
                    continue

            self.DATA_CONTAINER.append(instance)

    def backup_urls(self):
        if self.storage is None:
            self.storage = FileStorage(settings.MEDIA_PATH)

        async def write_cache_file():
            data = {
                'spider': self.__class__.__name__,
                'spider_uuid': self.spider_uuid,
                'timestamp': self.get_current_date.strftime('%Y-%M-%d %H:%M:%S'),
                'urls_to_visit': self.urls_to_visit,
                'visited_urls': self.visited_urls
            }
            self.storage.save_or_create(f'{settings.CACHE_FILE_NAME}.json', data)

        async def write_seen_urls():
            sorted_urls = []
            for url in self.list_of_seen_urls:
                bisect.insort(sorted_urls, url)

            self.storage.save_or_create('seen_urls.csv', sorted_urls, adapt_list=True)

        # async def write_cache_file():
        #     d = self.get_current_date.strftime('%Y-%M-%d %H:%M:%S')
        #     urls_data = {
        #         'spider': self.__class__.__name__,
        #         'spider_uid': self.spider_uuid,
        #         'timestamp': d,
        #         'urls_to_visit': self.urls_to_visit,
        #         'visited_urls': self.visited_urls
        #     }
        #     file_readers.write_json_document(
        #         f'{settings.CACHE_FILE_NAME}.json',
        #         urls_data
        #     )

        # async def write_seen_urls():
        #     sorted_urls = []
        #     for url in self.list_of_seen_urls:
        #         bisect.insort(sorted_urls, url)

        #     file_readers.write_csv_document(
        #         'seen_urls.csv',
        #         sorted_urls,
        #         adapt_data=True
        #     )

        async def main():
            # aws = [write_cache_file(), write_seen_urls()]
            
            t1 = asyncio.create_task(write_cache_file())
            t2 = asyncio.create_task(write_seen_urls())

            aws = [t1, t2]
            for aw in asyncio.as_completed(aws):
                await aw

        asyncio.run(main())

    def urljoin(self, path):
        """Returns the domain of the current
        website"""
        path = str(path).strip()
        result = urljoin(self.get_origin, path)
        return URL(unquote(result))

    def run_url_filters(self, valid_urls):
        """Excludes urls in the list of collected
        urls based on the value of the functions in
        `url_filters`. All conditions should be true
        in order for the url be considered valid to
        be visited"""
        if self._meta.url_ignore_tests:
            results = defaultdict(list)
            for url in valid_urls:
                truth_array = results[url]
                for instance in self._meta.url_ignore_tests:
                    truth_array.append(instance(url))

            urls_kept = set()
            urls_removed = set()
            final_urls_filtering_audit = OrderedDict()

            for url, truth_array in results.items():
                final_urls_filtering_audit[url] = any(truth_array)

                # Expect all the test results to
                # be true. Otherwise the url is invalid
                if any(truth_array):
                    urls_removed.add(url)
                    continue
                urls_kept.add(url)

            logger.info(
                f"Filters completed. {len(urls_removed)} "
                "url(s) removed"
            )
            return urls_kept
        return valid_urls

    def check_urls(self, urls, refresh=False):
        raw_urls = set(urls)

        if self.performance_audit.iteration_count > 0:
            logger.info(f"Found {len(raw_urls)} url(s) in total on this page")

        raw_urls_objs = list(map(lambda x: URL(x), raw_urls))

        # rename to: ignore_page_tests
        if self._meta.url_gather_ignore_tests:
            pass

        valid_urls = set()
        invalid_urls = set()

        for url in raw_urls_objs:
            if url.is_path:
                url = self.urljoin(url)

            if refresh:
                # If we are for example paginating a page,
                # then we only need to keep the new urls
                # that have appeared and that we have
                # not yet seen
                if url in self.list_of_seen_urls:
                    invalid_urls.add(url)
                    continue

            if not url.is_same_domain(self.start_url):
                invalid_urls.add(url)
                continue

            if url.is_empty:
                invalid_urls.add(url)
                continue

            if url.has_fragment:
                invalid_urls.add(url)
                continue

            if (url.url_object.path == '/' and
                    self.start_url.url_object.path == '/'):
                invalid_urls.add(url)
                continue

            if self._meta.ignore_images:
                if url.is_image:
                    invalid_urls.add(url)
                    continue

            if url in self.visited_urls:
                invalid_urls.add(url)
                continue

            if url in self.list_of_seen_urls:
                invalid_urls.add(url)
                continue

            valid_urls.add(url)

        self.list_of_seen_urls.update(valid_urls)
        self.list_of_seen_urls.update(invalid_urls)

        if valid_urls:
            logger.info(f'Kept {len(valid_urls)} url(s) as valid to visit')

        newly_discovered_urls = []
        for url in valid_urls:
            if url not in self.list_of_seen_urls:
                newly_discovered_urls.append(url)

        if newly_discovered_urls:
            logger.info(
                f"Discovered {len(newly_discovered_urls)} "
                "unseen url(s)"
            )
        return valid_urls

    def add_urls(self, urls, refresh=False):
        """Manually add urls to the current urls to
        visit list. This is useful for cases where urls are
        nested in other elements than links and that
        cannot actually be retrieved by the spider

        * Check that the url was not already seen and therefore
          invalid be navigated to"""
        checked_urls = self.check_urls(urls, refresh=refresh)
        filtered_urls = self.run_url_filters(checked_urls)
        self.urls_to_visit.update(filtered_urls)

    def calculate_performance(self):
        pass

    def current_page_actions(self, current_url, **kwargs):
        """Custom actions to execute on the current page. 

        >>> class MyCrawler(SiteCrawler):
        ...     def current_page_actions(self, current_url, **kwargs):
        ...         text = self.driver.find_element('h1').text
        """
        return NotImplemented

    def post_navigation_actions(self, current_url, **kwargs):
        """Actions to run on the page immediately after
        the crawler has visited a page e.g. clicking
        on cookie button banner"""
        return NotImplemented

    def before_next_page_actions(self, current_url, next_url, **kwargs):
        """Actions to run once the page was visited and that
        all user actions were performed. This method runs just 
        after the `wait_time` has expired"""
        return NotImplemented

    def after_fail(self):
        """Dumps the collected results to a file when the driver
        meets and exception during the crawling process. This method
        can be customized with a custome action that you would want
        to run
        """
        return NotImplemented

    def after_data_save(self, data):
        return NotImplemented

    def before_start(self, start_urls, *args, **kwargs):
        return NotImplemented


class OnPageActionsMixin:
    def click_consent_button(self, element_id=None, element_class=None, before_click_wait_time=2, wait_time=None):
        """Click the consent to cookies button which often
        tends to appear on websites"""
        try:
            element = None
            if element_id is not None:
                element = self.driver.find_element(By.ID, element_id)

            if element_class is not None:
                element = self.driver.find_element(
                    By.CLASS_NAME,
                    element_class
                )

            if element is not None and before_click_wait_time:
                time.sleep(before_click_wait_time)

            element.click()
        except:
            logger.info('Consent button not found')
        finally:
            # Some websites might create an issue when
            # trying to gather the urls of page just
            # after clicking the consent button. Using
            # the wait time can prevent the stale element
            # error from being raised
            if wait_time is not None:
                time.sleep(wait_time)


class SiteCrawler(OnPageActionsMixin, BaseCrawler):
    def __init__(self, browser_name=None):
        super().__init__(browser_name=browser_name)

        self.start_date = get_current_date(timezone=self.timezone)
        self.end_date = None
        self.performance_audit = Performance()
        self.performance_audit.timezone = self.timezone

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass
        logger.info('Project stopped')

    @staticmethod
    def transform_string_urls(urls):
        for url in urls:
            yield URL(url)

    # async def start_udp_server(self, host='localhost', port=65432):
    #     server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     server.bind((host, port))

    #     def handle_client(data, address, server):
    #         server.sendto(data.encode(), address)

    #     with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    #         while True:
    #             data, address = server.recvfrom(1024)
    #             executor.submit(handle_client, data, address, server)

    def load_storage(self, python_path):
        """Use this function to load the different
        storages that the user has implemented to be
        used for the spider"""
        try:
            default = settings.STORAGES.get('default')
            klass = import_from_module(default)
        except Exception:
            raise ValueError(
                "Could not load storage "
                f"module: {python_path}"
            )

        if not issubclass(klass, BaseStorage):
            raise ValueError(
                f"{klass} should be an instance "
                "of BaseStorage"
            )

        return klass

    def before_start(self, start_urls, *args, **kwargs):
        if self._meta.debug_mode:
            logger.debug('Starting Kryptone in debug mode')
        else:
            logger.info('Starting Kryptone')

        klass = self.load_storage(settings.STORAGES.get('default'))
        if getattr(klass, 'file_based'):
            self.storage = klass(settings.MEDIA_FOLDER)

        for path in settings.STORAGES.get('backends', []):
            other = self.load_storage(path)
            if getattr(other, 'file_based'):
                self.additional_storages.append(other(settings.MEDIA_FOLDER))
                continue
            self.additional_storages.append(other())

        logger.info(f'{self.__class__.__name__} ready to crawl website')

        start_urls = start_urls or self._meta.start_urls
        if (hasattr(start_urls, 'resolve_generator') or
                inspect.isgenerator(start_urls)):
            start_urls = list(start_urls)
        start_urls = list(self.transform_string_urls(start_urls))

        # If we have absolutely no start_url and at the
        # same time we have no start_urls, raise an error
        if not start_urls:
            raise exceptions.BadImplementationError(
                "No start urls was used. Provide start urls list "
                "in spider.Meta to start crawling a list of urls"
            )

        self.start_url = URL(start_urls[-1])
        self.add_urls(start_urls)

    def start(self, start_urls=[], **kwargs):
        self.before_start(start_urls, **kwargs)

        if self._meta.debug_mode:
            logger.warning("Calling start in debug mode will have no effect")
            return False

        self.driver.maximize_window()

        next_execution_date = None
        while self.urls_to_visit:
            if next_execution_date is not None:
                if self.get_current_date < next_execution_date:
                    continue

            current_url = URL(self.urls_to_visit.pop())
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url.is_empty:
                continue

            if not current_url.is_same_domain(self.start_url):
                continue

            logger.info(f'Going to url: {current_url}')

            try:
                self.driver.get(str(current_url))
            except Exception as e:
                logger.critical(f'Failed to go to: {current_url}: {e.args}')
                continue

            try:
                # Always wait for the body section of
                # the page to be located  or visible
                wait = WebDriverWait(self.driver, 5)

                condition = EC.presence_of_element_located(
                    (By.TAG_NAME, 'body')
                )
                wait.until(condition)
            except:
                logger.critical('Body element of page was not located')
                continue
            else:
                self.post_navigation_actions(current_url)

            self.visited_urls.add(current_url)

            if self._meta.crawl:
                self.add_urls(self.collect_page_urls())
                self.backup_urls()

            current_page_actions_params = {}

            try:
                self.current_page_actions(
                    current_url,
                    **current_page_actions_params
                )
            except TypeError as e:
                logger.error(e)
                raise TypeError(
                    "'self.current_page_actions' should "
                    "be able to accept arguments"
                )
            except Exception as e:
                logger.error(e)
                raise ExceptionGroup(
                    "An exception occured while trying "
                    "to execute 'current_page_actions'",
                    [
                        Exception(e),
                        exceptions.SpiderExecutionError()
                    ]
                )
            else:
                # Refresh the urls once the
                # user actions have been completed
                # for example scrolling down a page
                # that could generate new urls to
                # disover or changing a filter
                if self._meta.crawl:
                    self.add_urls(self.collect_page_urls(), refresh=True)
                    self.backup_urls()

            try:
                next_url = self.urls_to_visit[-1]
            except:
                pass
            else:
                self.before_next_page_actions(current_url, next_url)

            if self._meta.router is not None:
                pass

            if self._meta.crawl:
                pass

            wait_time = settings.WAIT_TIME
            if settings.WAIT_TIME_RANGE:
                wait_time = random.randrange(
                    settings.WAIT_TIME_RANGE[0],
                    settings.WAIT_TIME_RANGE[1],
                )

            next_execution_date = (
                self.get_current_date +
                datetime.timedelta(seconds=wait_time)
            )

            self.performance_audit.add_iteration_count()
            if len(self.urls_to_visit) == 0:
                self.performance_audit.end_date = self.get_current_date
                self.performance_audit.calculate_duration()

            logger.info(f"Next execution time: {next_execution_date}")

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

    def resume(self, windows=1, **kwargs):
        """Resume a previous crawling sessiong by reloading
        data from the urls to visit and visited urls json files
        if present. The presence of previous data is checked 
        in order by doing the following :

            * Redis is checked as the primary database for a cache
            * Memcache is checked in second place
            * Finally, the file cache is used as a final resort if none exists
        """

    def start_from_sitemap_xml(self, url, windows=1, **kwargs):
        pass

    def start_from_json(self, windows=1, **kwargs):
        pass

    def boost_start(self, start_urls=[], *, windows=1, **kwargs):
        pass
