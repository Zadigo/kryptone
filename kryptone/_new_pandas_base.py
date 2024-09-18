import dataclasses
import datetime
import inspect
import os
import pathlib
import random
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field, is_dataclass
from functools import cached_property
from typing import List, Union
from urllib.parse import unquote, urljoin, urlparse, urlunparse
from uuid import uuid4

import pandas
import pytz
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import exceptions, logger
from kryptone.conf import settings
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL

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
    ... browser.get('http://example.com')
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

    if headless:
        # Allows Selenium to be launched
        # in headless mode
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


@dataclass
class Performance:
    iteration_count: int = 0
    start_date: datetime.datetime = field(
        default_factory=datetime.datetime.now
    )
    end_date: datetime.datetime = field(
        default_factory=datetime.datetime.now
    )
    error_count: int = 0
    duration: int = 0

    def calculate_duration(self):
        self.duration = (self.start_date - self.end_date)

    def add_error_count(self):
        self.error_count = self.error_count + 1

    def add_iteration_count(self):
        self.iteration_count = self.iteration_count + 1

    def json(self) -> List[
        OrderedDict[str, Union[int, float, datetime.datetime]]]: ...


class CrawlerOptions:
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

    def add_meta_options(self, options):
        for name, value in options:
            if name not in DEFAULT_META_OPTIONS:
                raise ValueError(
                    f"Meta for model '{self.verbose_name}' received "
                    f"an illegal option '{name}'"
                )
            setattr(self, name, value)

    def prepare(self):
        pass


class Crawler(type):
    def __new__(cls, name, bases, attrs):
        super_new = super().__new__

        parents = [b for b in bases if isinstance(b, Crawler)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, attrs)
        if name == 'SiteCrawler':
            return new_class

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
    timezone = 'UTC'
    start_url = None

    container = None
    saved_data = None

    def __init__(self, browser_name=None, debug=False, after_seconds=None):
        self.browser_name = browser_name
        self.after_seconds = after_seconds
        self.driver = None
        self.debug = debug
        self.spider_uuid = uuid4()

        if not self.debug:
            self.driver = get_selenium_browser_instance(
                browser_name=browser_name or self.browser_name,
                headless=settings.HEADLESS,
                load_images=settings.LOAD_IMAGES,
                load_js=settings.LOAD_JS
            )

        self.seen_urls = pandas.DataFrame({'urls': []})
        self.urls_to_visit = pandas.DataFrame([])
        self.urls_to_visit_list = []

        self.saved_data = None
        if self.container is not None:
            if not is_dataclass(self.container):
                raise ValueError('Container should be a dataclass')

            fields = dataclasses.fields(self.container)
            data = defaultdict(list)
            for field in fields:
                data[field.name]
            self.saved_data = pandas.DataFrame(data)

    def __repr__(self):
        name = self.__class__.__new__()
        return f'<{name}:>'

    def __hash__(self):
        return hash((self.spider_uuid))

    @property
    def collect_page_urls(self):
        """Returns all the links present on the
        currently visited page"""
        found_urls = []
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

    @property
    def visited_urls(self):
        return self.urls_to_visit.query('visited == True')

    @property
    def count_of_visited_urls(self):
        return self.visited_urls.urls.count()

    @property
    def count_of_urls_to_visit(self):
        return len(self.urls_to_visit_list)

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
        return urlunparse((
            self.start_url.scheme,
            self.start_url.netloc,
            None,
            None,
            None,
            None
        ))

    @cached_property
    def calculate_completion_percentage(self):
        return len(self.visited_urls) / len(self.urls_to_visit)

    def urljoin(self, path):
        """Returns the domain of the current
        website"""
        path = str(path).strip()
        result = urljoin(self.get_origin, path)
        return URL(unquote(result))

    def run_url_filters(self, valid_urls):
        return valid_urls

    def create_dataframe_from_urls(self, urls=[]):
        url_objs = self.transform_string_urls(urls)
        local_df = pandas.DataFrame({'urls': url_objs})
        local_df['visited'] = False
        local_df['date'] = None
        local_df['error'] = None
        return local_df

    def load_file(self, name):
        path = pathlib.Path(name)
        if path.is_file() and path.exists():
            if path.suffix == '.json':
                local_df = pandas.read_json(path)
            elif path.suffix == '.csv':
                local_df = pandas.read_csv(path)

            if 'urls' not in local_df.columns:
                raise ValueError('File should contain urls column')

            local_df['visited'] = False
            local_df['date'] = None
            local_df['error'] = None
            self.add_urls(local_df)

    def check_urls(self, list_or_dataframe):
        """Runs a series of checks on the incoming urls by
        doing the following:

        * Ensure that the url is structurally correct

        """
        if isinstance(list_or_dataframe, list):
            local_df = self.create_dataframe_from_urls(urls=list_or_dataframe)
        elif isinstance(list_or_dataframe, pandas.DataFrame):
            local_df = list_or_dataframe
        else:
            raise ValueError(
                "list_or_dataframe should "
                "be a dataframe object"
            )

        if self.performance_audit.iteration_count > 0:
            logger.info(
                f"Found {len(list_or_dataframe)} "
                "url(s) in total on this page"
            )

        # 1. Check that the urls that we are trying to add
        # do not already exist in the database of seen urls
        seen_urls_list = self.seen_urls.urls.tolist()
        unseen_urls_tests = local_df.isin({'urls': seen_urls_list})
        unseen_urls = local_df[unseen_urls_tests.urls == False]

        no_duplicates = unseen_urls[~unseen_urls.duplicated()]
        no_duplicates['ignore'] = False

        if self._meta.url_gather_ignore_tests:
            pass

        def url_basic_check_test(value):
            url_instance = URL(value)

            if not url_instance.is_same_domain(self.start_url):
                return True

            if url_instance.is_empty:
                return True

            if url_instance.has_fragment:
                return True

            if (url_instance.url_object.path == '/' and
                    self.start_url.url_object.path == '/'):
                return True

            if self._meta.ignore_queries:
                if url_instance.has_queries():
                    return True

            if self._meta.ignore_images:
                if url_instance.is_image:
                    return True
            return False

        no_duplicates['ignore'] = no_duplicates.urls.map(url_basic_check_test)
        valid_urls = no_duplicates[~no_duplicates.ignore]

        # Regardless of whether the url is valid
        # or not, it should be registered as a
        # seen url
        self.seen_urls = pandas.concat(
            [
                self.seen_urls,
                local_df[['urls']]
            ]
        )
        self.seen_urls.sort_values('urls')

        return valid_urls.get(['urls', 'visited', 'date', 'error'])

    def merge_urls(self, dataframe):
        """Function that merges the urls from a dataframe
        to the ones present in the existing `urls_to_visit`
        one. This function does not check that the urls were
        already seen or visited and should not be used directly
        to add urls to the main dataframe"""
        if not isinstance(dataframe, pandas.DataFrame):
            raise ValueError(
                "dataframe should be an instance "
                "of pandas.DataFrame"
            )

        local_df = pandas.concat(
            [
                self.urls_to_visit,
                dataframe
            ]
        )

        local_df = local_df.reset_index(drop=True)
        local_df.sort_values('urls')

        self.urls_to_visit = local_df
        self.urls_to_visit_list = local_df.urls.tolist()

    def add_urls(self, list_or_dataframe):
        """Main entrypoint to add urls to the main container
        of urls to visit. It checks that the url was already
        seen and ensures that it will not be visited twice.
        It also calls `check_urls` to ensure that incorrect
        urls do not get added to the main container of urls
        to navigate

        * Check that the url was either already seen and therefore
          invalid be navigated to or does not contain a normal format

        * Run user custom url filters that invalidate or validate certain
          types of urls to exclude"""
        # 1. Check the urls before adding them to the list of
        # urls to visit + list of seen urls
        checked_urls = self.check_urls(list_or_dataframe)

        # 2. Run the custom user filters
        filtered_urls = self.run_url_filters(checked_urls)

        if filtered_urls.urls.count() > 0:
            logger.info(
                f'Added {filtered_urls.urls.count()} more url(s) to visit')
            self.merge_urls(filtered_urls)

    def calculate_performance(self):
        pass

    def current_page_actions(self, url, *args, **kwargs):
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
        self.urls_to_visit.to_csv('visited_urls.csv', index_label='id')

    def after_fail(self, current_url, message):
        self.urls_to_visit.loc[
            self.urls_to_visit.urls == current_url,
            'error'
        ] = message
        self.urls_to_visit.to_csv('visited_urls.csv', index_label='id')

    def after_data_save(self, dataframe):
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.performance_audit = Performance()

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

    @staticmethod
    def reverse_transform_url_objects(urls):
        for url in urls:
            yield str(url)

    def before_start(self, start_urls, *args, **kwargs):
        if self._meta.debug_mode:
            logger.debug('Starting Kryptone in debug mode...')
        else:
            logger.info('Starting Kryptone...')

        # self.driver.maximize_window()
        logger.info(f'{self.__class__.__name__} ready to crawl website')

        start_urls = start_urls or self._meta.start_urls
        if (hasattr(start_urls, 'resolve_generator') or
                inspect.isgenerator(start_urls)):
            start_urls = list(start_urls)
        start_urls = list(self.transform_string_urls(start_urls))

        # If we have absolutely no start_url and at the
        # same time we have no start_urls, raise an error
        if self.start_url is None and not start_urls:
            raise exceptions.BadImplementationError(
                "No start url was used. Provide either a "
                "start url or start urls to crawl in the Meta"
            )

        if self.start_url is None and start_urls:
            self.start_url = start_urls[-1]
            self.list_of_seen_urls.update(start_urls)
        else:
            self.start_url = URL(self.start_url)
            start_urls.append(self.start_url)
        self.add_urls(start_urls)

    def start(self, start_urls=[], filename=None, sort_data_by=None):
        if filename is not None:
            self.load_file(filename)

        self.before_start(start_urls)

        if self.after_seconds is not None:
            time.sleep(self.after_seconds)

        next_execution_date = None
        while self.urls_to_visit_list:
            if next_execution_date is not None:
                if self.get_current_date < next_execution_date:
                    continue

            current_url = self.urls_to_visit_list.pop()
            item = self.urls_to_visit.loc[self.urls_to_visit.urls == current_url]
            # self.before_page_actions(current_url)

            try:
                if self.debug:
                    logger.debug('Kryptone is running debug mode')
                else:
                    self.driver.get(str(current_url))
            except Exception as e:
                self.performance_audit.add_error_count()
                self.after_fail(current_url, e.args)
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

            if not self._meta.debug_mode:
                if self._meta.crawl:
                    self.add_urls(self.collect_page_urls)
                    # new_urls_df = self.check_urls(self.collect_page_urls)
                    # self.add_urls(new_urls_df)

            logger.info(f'Going to url: {current_url}')

            self.urls_to_visit.loc[item.index, 'visited'] = True
            self.urls_to_visit.loc[
                item.index,
                'date'
            ] = self.get_current_date

            self.before_next_page_actions(
                current_url, self.urls_to_visit_list[-1])

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

            if len(self.urls_to_visit_list) == 0:
                self.performance_audit.end_date = self.get_current_date
                self.performance_audit.calculate_duration()

            logger.info(f"Next execution time: {next_execution_date}")

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

    def resume(self, windows=1, **kwargs):
        pass

    def start_from_sitemap_xml(self, url, windows=1, **kwargs):
        pass

    def start_from_json(self, windows=1, **kwargs):
        pass

    def boost_start(self, start_urls=[], *, windows=1, **kwargs):
        pass
