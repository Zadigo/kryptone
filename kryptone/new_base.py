import asyncio
import bisect
import datetime
import os
import random
import time
from collections import OrderedDict, defaultdict, namedtuple
from urllib.parse import unquote, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import pandas
import pytz
import requests
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

from kryptone import constants, exceptions, logger
from kryptone.conf import settings
from kryptone.db.tables import Database
from kryptone.utils import file_readers
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.file_readers import LoadStartUrls
from kryptone.utils.iterators import (AsyncIterator, PagePaginationGenerator,
                                      URLGenerator)
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL, pathlib
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
        self.database = None

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
        # directly in "start_urls"
        if isinstance(self.start_urls, (URLGenerator, PagePaginationGenerator)):
            self.start_urls = list(self.start_urls)

        if isinstance(self.start_urls, list):
            start_urls = []
            for item in self.start_urls:
                if isinstance(item, (URLGenerator, PagePaginationGenerator)):
                    start_urls.extend(list(item))
                    continue

                if isinstance(item, str):
                    start_urls.extend([item])
                    continue

            self.start_urls = start_urls

        if self.database is not None:
            if not isinstance(self.database, Database):
                raise ValueError(
                    f"{type(self.database)} should be "
                    "an instance of Database"
                )


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
    browser_name = None
    timezone = 'utc'
    default_scroll_step = 80

    def __init__(self, browser_name=None):
        self._start_url_object = None

        self.urls_to_visit = pandas.DataFrame(
            [],
            columns=['urls', 'visited', 'date']
        )
        self.list_of_seen_urls = pandas.DataFrame(
            [],
            columns=['urls', 'date']
        )

        self.driver = get_selenium_browser_instance(
            browser_name=browser_name or self.browser_name,
            headless=settings.HEADLESS,
            load_images=settings.LOAD_IMAGES,
            load_js=settings.LOAD_JS
        )
        self.url_distribution = defaultdict(list)

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    @property
    def get_page_link_elements(self):
        """Returns all the links present on the
        currently visited page"""
        if self._meta.restrict_search_to:
            found_urls = []
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

            # If no urls were found in the specific
            # section of the page, we'll just return
            # the whole page urls
            if found_urls:
                return found_urls

        urls = self.driver.execute_script(
            """
        const urls = Array.from(document.querySelectorAll('a'))
        return urls.map(x => x.href)
        """
        )
        return urls

    @property
    def get_title_element(self):
        return self.driver.find_element(By.TAG_NAME, 'title')

    @property
    def get_origin(self):
        return urlunparse((
            self._start_url_object.scheme,
            self._start_url_object.netloc,
            None,
            None,
            None,
            None
        ))

    def _backup_urls(self):
        pass

    def _get_robot_txt_parser(self):
        pass

    def urljoin(self, path):
        pass

    def url_structural_check(self, url):
        pass

    def url_filters(self, valid_urls):
        pass

    def url_rule_test_filter(self, valid_urls):
        pass

    def add_urls(self, *urls_or_paths):
        pass

    def get_page_urls(self, current_url, refresh=False):
        """Gets all the urls present on the
        actual visited page. Fragments, empty strings
        a ignored by default. Query strings can be ignored using
        `Meta.ignore_queries` and images with `Meta.ignore_images`.

        By default, all the urls that were found during a crawling
        session are save in `list_of_seen_urls` and only valid urls
        to visit are included in `urls_to_visit`"""
        raw_urls = self.get_page_link_elements

        df = pandas.DataFrame({'urls': raw_urls})
        df = df[~df['urls'].isna()]
        df['visited'] = False
        df['date'] = get_current_date()
        df['is_valid'] = False

        logger.info(
            f"Found {df.urls.count()} url(s) "
            "in total on this page"
        )

        # Specifically indicate to the crawler to
        # not try and collect urls on pages that
        # match the specified regex values
        if self._meta.url_gather_ignore_tests:
            pass

        def url_structural_check(url):
            if url is None:
                return None
            clean_url = unquote(url)
            if clean_url.startswith('/'):
                clean_url = self.urljoin(clean_url)
            return clean_url

        df['urls'] = df['urls'].map(url_structural_check)

        self.list_of_seen_urls = pandas.concat([
            self.list_of_seen_urls,
            df[['urls']]
        ])

        visited_urls = self.urls_to_visit[self.urls_to_visit['visited'] == True]

        for item in df.itertuples(name='Url'):
            current_url = df.loc[item.Index, 'urls']
            url = URL(current_url)

            if url.url_object.netloc != self._start_url_object.netloc:
                continue

            if current_url == '':
                continue

            if url.url_object.fragment:
                continue

            if url.url_object.path == '/' and self._start_url_object.path == '/':
                continue

            if self._meta.ignore_queries:
                pass

            if self._meta.ignore_images:
                pass

            is_visited_df = visited_urls[df['urls'].isin(visited_urls)]
            if is_visited_df.urls.count() > 0:
                continue

            df.loc[item.Index, 'is_valid'] = True

        valid_urls = df.query('is_valid == True')
        valid_urls = valid_urls.drop_duplicates()
        invalid_urls = df.query('is_valid == True')
        logger.info(
            f"Kept {valid_urls.urls.count()} url(s) "
            "as valid to visit"
        )

        newly_discovered_urls = None
        self.urls_to_visit = pandas.concat([
            self.urls_to_visit,
            valid_urls[['urls', 'visited', 'date']]
        ], ignore_index=True)

    def click_consent_button(self, element_id=None, element_class=None, before_click_wait_time=2, wait_time=None):
        pass

    def calculate_performance(self):
        pass

    def post_navigation_actions(self, current_url, **kwargs):
        """Actions to run on the page immediately after
        the crawler has visited a page e.g. clicking
        on cookie button banner"""
        pass

    def before_next_page_actions(self, current_url, **kwargs):
        """Actions to run once the page was visited and that
        all user actions were performed. This method runs just 
        after the `wait_time` has expired"""
        pass

    def current_page_actions(self, current_url, **kwargs):
        """Custom actions to execute on the current page. 

        >>> class MyCrawler(SiteCrawler):
        ...     def current_page_actions(self, current_url, **kwargs):
        ...         text = self.driver.find_element('h1').text
        """
        pass

    def create_dump(self):
        """Dumps the collected results to a file when the driver
        meets and exception during the crawling process. This method
        can be customized with a custome action that you would want
        to run
        """


class SiteCrawler(BaseCrawler):
    start_url = None

    def __init__(self, browser_name=None):
        super().__init__(browser_name=browser_name)

        self._start_date = get_current_date(timezone=self.timezone)
        self._start_time = time.time()
        self._end_time = None

    @classmethod
    def create(cls, **params):
        instance = cls(**params)
        return instance

    def before_start(self, start_urls, **kwargs):
        """This function initializes important sections of
        the spider before running `start` function"""
        logger.info(f'{self.__class__.__name__} ready to crawl website')
        self.driver.maximize_window()

        if self._meta.debug_mode:
            logger.info('Starting Kryptone in debug mode...')
        else:
            logger.info('Starting Kryptone...')

        start_urls = start_urls or self._meta.start_urls

        # If we have absolutely no start_url and at the
        # same time we have no start_urls, raise an error
        if self.start_url is None and not start_urls:
            raise exceptions.BadImplementationError(
                "No start url. Provide either a "
                "start url or start urls in the Meta"
            )

        if self.start_url is None and start_urls:
            if isinstance(start_urls, (file_readers.LoadStartUrls)):
                start_urls = list(start_urls)

            self.list_of_seen_urls = pandas.concat([
                self.list_of_seen_urls,
                pandas.DataFrame({'urls': start_urls}, )]
            )
            item = self.list_of_seen_urls.loc[0, 'urls']
            self.start_url = item.url
        self._start_url_object = urlparse(self.start_url)

        # If we have no urls to visit in
        # the array, try to eventually
        # populate the list with existing ones
        if not self.urls_to_visit.urls.count() == 0:
            # Start spider from .xml page
            is_xml_page = self.start_url.endswith('.xml')
            if is_xml_page:
                start_urls = self.start_from_sitemap_xml(self.start_url)
            else:
                # Add the start_url to the list of
                # urls to visit - as entrypoint
                self.add_urls(self.start_url)

        if start_urls:
            self.add_urls(*start_urls)

        if self.start_url is not None:
            df = pandas.DataFrame([{
                    'urls': self.start_url,
                    'visited': False,
                    'date': get_current_date()
                }]
            )
            self.urls_to_visit = pandas.concat([
                    self.urls_to_visit,
                    df 
                ], ignore_index=True
            )


    def resume(self, windows=1, **kwargs):
        """Resume a previous crawling sessiong by reloading
        data from the urls to visit and visited urls json files
        if present. The presence of previous data is checked 
        in order by doing the following :

            * Redis is checked as the primary database for a cache
            * Memcache is checked in second place
            * Finally, the file cache is used as a final resort if none exists
        """

    def start_from_sitemap_xml(self, url, **kwargs):
        """Start crawling from the XML sitemap
        page of a given website

        >>> instance = BaseCrawler()
        ... instance.start_from_html_sitemap("http://example.com/sitemap.xml")
        """

    def start_from_html_sitemap(self, url, **kwargs):
        """Start crawling from the sitemap HTML page
        section of a given website

        >>> instance = BaseCrawler()
        ... instance.start_from_html_sitemap("http://example.com/sitemap.html")
        """

    def start(self, start_urls=[], **kwargs):
        """This is the main entrypoint to start the
        spider. This will open the browser, open an
        url and call `current_page_actions` which are
        custom user defined actions to run the current
        page.

        This method could be started inline as shown below:

        >>> instance = SiteCrawler()
        ... instance.start(start_urls=["http://example.com"])

        You can specify `current_page_actions` by subclassing SiteCrawler:

        >>> class MyCrawler(SiteCrawler):
        ...     start_url = 'http://example.com'
        ...
        ...     def current_page_actions(self, current_url, **kwargs):
        ...         pass
        ... 
        ... instance = MyCrawler()
        ... instance.start()
        """
        self.before_start(start_urls, **kwargs)

        # wait_time = settings.WAIT_TIME
        wait_time = 3

        can_crawl = True
        while can_crawl:
            non_completed_urls_df = self.urls_to_visit[self.urls_to_visit['visited'] == False]
            if non_completed_urls_df['visited'].count() == 0:
                can_crawl = False
                continue

            indexes = [
                index for index in non_completed_urls_df.index
                if isinstance(index, int)
            ]
            selected_index = random.choice(indexes)
            selected_url = self.urls_to_visit.loc[selected_index, 'urls']

            logger.info(
                f"{len(non_completed_urls_df.count())} "
                "urls left to visit"
            )

            if selected_url is None:
                continue

            selected_url_object = URL(selected_url)
            # If we are not on the same domain as the
            # starting url: *stop*. we are not interested
            # in exploring the whole internet
            if selected_url_object.url_object.netloc != self._start_url_object.netloc:
                continue

            # By security measure, do not go to an url
            # that is an image if it happened to be in
            # the urls_to_visit
            if self._meta.ignore_images:
                if selected_url_object.is_image:
                    continue

            logger.info(f'Going to url: {selected_url}')

            self.driver.get(str(selected_url))
            try:
                # Always wait for the body section of
                # the page to be located  or visible
                wait = WebDriverWait(self.driver, 5)
                wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
            except:
                logger.error('Body element of page was not detected')
            self.post_navigation_actions(selected_url)

            if self._meta.crawl:
                self.get_page_urls(selected_url)
                self._backup_urls()

            current_page_actions_params = {}

            try:
                # Run custom user actions once
                # everything is completed
                self.current_page_actions(
                    selected_url,
                    **current_page_actions_params
                )
            except TypeError as e:
                logger.error(e)
                raise TypeError(
                    "'self.current_page_actions' should be able to accept arguments"
                )
            except Exception as e:
                logger.error(e)
                raise ExceptionGroup(
                    "An exception occured while trying "
                    "to execute 'self.current_page_actions'",
                    [
                        Exception(e),
                        exceptions.SpiderExecutionError()
                    ]
                )
            # else:
            #     # Refresh the urls once the
            #     # user actions have been completed
            #     # for example scrolling down a page
            #     # that could generate new urls to
            #     # disover or changing a filter
            #     if self._meta.crawl:
            #         self.get_page_urls(selected_url, refresh=True)
            #         self._backup_urls()

            self.urls_to_visit.loc[selected_index, 'visited'] = True

            # Run routing actions aka, base on given
            # url path, route to a function that
            # would execute said task
            if self._meta.router is not None:
                self._meta.router.resolve(selected_url, self)

            if self._meta.crawl:
                self.calculate_performance()

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            if os.getenv('KYRPTONE_TEST_RUN') == 'True':
                break

            logger.info(f"Waiting {wait_time}s")
            time.sleep(wait_time)
            self.before_next_page_actions(selected_url)

    def boost_start(self, start_urls=[], *, windows=1, **kwargs):
        """Calling this method will make selenium open either
        multiple windows or multiple tabs for the project.$
        Selenium will open an url in each window or tab and
        sequentically call `current_page_actions` on the
        given page"""


class TestCrawler(SiteCrawler):
    # start_url = 'https://example.com'
    start_url = 'https://www.bershka.com/fr/h-woman.html'


c = TestCrawler(browser_name='Edge')
c.start()
