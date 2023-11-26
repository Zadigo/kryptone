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
from kryptone.utils.iterators import AsyncIterator, URLGenerator
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL, pathlib
from kryptone.webhooks import Webhooks

DEFAULT_META_OPTIONS = {
    'domains', 'url_ignore_tests',
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
        if isinstance(self.start_urls, URLGenerator):
            self.start_urls = list(self.start_urls)

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
    urls_to_visit = set()
    visited_urls = set()
    visited_pages_count = 0
    list_of_seen_urls = set()
    browser_name = None
    timezone = 'UTC'
    default_scroll_step = 80

    def __init__(self, browser_name=None):
        self._start_url_object = None

        self.driver = get_selenium_browser_instance(
            browser_name=browser_name or self.browser_name,
            headless=settings.HEADLESS,
            load_images=settings.LOAD_IMAGES,
            load_js=settings.LOAD_JS
        )
        self.url_distribution = defaultdict(list)

        # navigation.connect(collect_images_receiver, sender=self)

        # db_signal.connect(backends.airtable_backend, sender=self)
        # db_signal.connect(backends.notion_backend, sender=self)
        # db_signal.connect(backends.google_sheets_backend, sender=self)

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
        """Backs up the urls both in memory 
        and file cache which can then be resumed
        on a next run"""

        async def write_cache_file():
            d = get_current_date(timezone=self.timezone)
            urls_data = {
                'spider': self.__class__.__name__,
                'timestamp': d.strftime('%Y-%M-%d %H:%M:%S'),
                'urls_to_visit': list(self.urls_to_visit),
                'visited_urls': list(self.visited_urls)
            }
            file_readers.write_json_document(
                f'{settings.CACHE_FILE_NAME}.json',
                urls_data
            )

        async def write_seen_urls():
            sorted_urls = []
            for url in self.list_of_seen_urls:
                bisect.insort(sorted_urls, url)
            file_readers.write_csv_document('seen_urls.csv', sorted_urls, adapt_data=True)

        
        async def main():
            await write_cache_file()
            await write_seen_urls()

        asyncio.run(main())

        # db_signal.send(
        #     self,
        #     data_type='urls',
        #     urls_data=urls_data
        # )

    def _get_robot_txt_parser(self):
        """Checks if an url can be crawled
        using the Robots.txt file"""
        instance = RobotFileParser()
        robots_txt_url = urlunparse((
            self._start_url_object.scheme,
            self._start_url_object.netloc,
            'robots.txt',
            None,
            None,
            None
        ))
        instance.set_url(robots_txt_url)
        return instance

    def urljoin(self, path):
        """Returns the domain of the current
        website"""
        path = str(path).strip()
        result = urlunparse((
            self._start_url_object.scheme,
            self._start_url_object.netloc,
            path,
            None,
            None,
            None
        ))
        return unquote(result)

    def url_structural_check(self, url):
        """Checks the structure of an
        incoming url"""
        url = str(url)
        clean_url = unquote(url)
        if url.startswith('/'):
            clean_url = self.urljoin(clean_url)
        return clean_url, urlparse(clean_url)

    def url_filters(self, valid_urls):
        """Excludes urls in the list of urls to visit based
        on the return value of the function in `url_filters`.
        All conditions should be true for the url to be
        considered to be visited.
        """
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

    def add_urls(self, *urls_or_paths):
        """Manually add urls to the current urls to
        visit. This is useful for cases where urls are
        nested in other elements than links and that
        cannot actually be retrieved by the spider"""
        counter = 0
        valid_urls = set()
        invalid_urls = set()
        for url in urls_or_paths:
            if url is None:
                continue

            clean_url, url_object = self.url_structural_check(url)
            self.list_of_seen_urls.add(clean_url)

            if url in self.visited_urls:
                invalid_urls.add(url)
                continue

            if url in self.urls_to_visit:
                invalid_urls.add(url)
                continue

            if url_object.netloc == '' and url_object.path == '':
                invalid_urls.add(url)
                continue

            counter = counter + 1
            valid_urls.add(clean_url)
        filtered_valid_urls = self.url_filters(valid_urls)
        self.urls_to_visit.update(filtered_valid_urls)
        logger.info(f'{counter} url(s) added')

    def get_page_urls(self, current_url, refresh=False):
        """Gets all the urls present on the
        actual visited page"""
        raw_urls = set(self.get_page_link_elements)
        logger.info(f"Found {len(raw_urls)} url(s) in total on this page")

        # Specifically indicate to the crawler to
        # not try and collect urls on pages that
        # match the specified regex values
        if self._meta.url_gather_ignore_tests:
            matched_pattern = None
            for regex in self._meta.url_gather_ignore_tests:
                if current_url.test_url(regex):
                    matched_pattern = regex
                    break

            if matched_pattern is not None:
                self.list_of_seen_urls.update(raw_urls)
                logger.warning(
                    f"Url collection ignored on current url "
                    f"by '{matched_pattern}'"
                )
                return

        valid_urls = set()
        invalid_urls = set()
        for url in raw_urls:
            clean_url, url_object = self.url_structural_check(url)

            if refresh:
                # If we are for example paginating a page,
                # then we only need to keep the new urls
                # that have appeared and that we have
                # not yet seen
                if url in self.list_of_seen_urls:
                    invalid_urls.add(clean_url)
                    continue

            if url_object.netloc != self._start_url_object.netloc:
                invalid_urls.add(clean_url)
                continue

            if url is None or url == '':
                invalid_urls.add(clean_url)
                continue

            if url_object.fragment:
                invalid_urls.add(clean_url)
                continue

            if url.endswith('#'):
                invalid_urls.add(clean_url)
                continue

            if url_object.path == '/' and self._start_url_object.path == '/':
                invalid_urls.add(clean_url)
                continue

            if self._meta.ignore_queries:
                if url_object.query:
                    invalid_urls.add(clean_url)
                    continue

            if self._meta.ignore_images:
                url_as_path = pathlib.Path(clean_url)
                if url_as_path.suffix != '':
                    suffix = url_as_path.suffix.removeprefix('.')
                    if suffix in constants.IMAGE_EXTENSIONS:
                        invalid_urls.add(clean_url)
                        continue

            if clean_url in self.visited_urls:
                invalid_urls.add(clean_url)
                continue

            if clean_url in self.visited_urls:
                invalid_urls.add(clean_url)
                continue

            valid_urls.add(clean_url)

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

        filtered_valid_urls = self.url_filters(valid_urls)
        self.urls_to_visit.update(filtered_valid_urls)

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
                """return window.scrollY"""
            )
            if stop_at is not None and current_position > stop_at:
                can_scroll = False

            new_scroll_pixels = new_scroll_pixels + increment
            time.sleep(wait_time)

    def click_consent_button(self, element_id=None, element_class=None, wait_time=None):
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
        finally:
            # Some websites might create an issue when
            # trying to gather the urls of page just
            # after clicking the consent button. Using
            # the wait time can prevent the stale element
            # error from being raised
            if wait_time is not None:
                time.sleep(wait_time)

    def scroll_page_section(self, xpath=None, css_selector=None):
        """Scrolls a specific portion on the page"""
        if css_selector:
            selector = """const mainWrapper = document.querySelector('{condition}')"""
            selector = selector.format(condition=css_selector)
        else:
            selector = self.evaluate_xpath(xpath)
            # selector = """const element = document.evaluate("{condition}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)"""
            # selector = selector.format(condition=xpath)

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

    def calculate_performance(self):
        """Calculate the overall spider performance"""
        # Calculate global performance
        async def performance():
            self._end_date = get_current_date(timezone=self.timezone)
            days = (self._start_date - self._end_date).days
            completed_time = round(time.time() - self._start_time, 1)
            days = 0 if days < 0 else days
            return self.performance_audit(days, completed_time)

        # Calculate performance related to urls
        async def performance_urls():
            total_urls = sum([len(self.visited_urls), len(self.urls_to_visit)])
            result = len(self.visited_urls) / total_urls
            percentage = round(result * 100, 3)
            logger.info(f'{percentage}% of total urls visited')

            return self.urls_audit(
                count_urls_to_visit=len(self.urls_to_visit),
                count_visited_urls=len(self.visited_urls),
                total_urls=total_urls,
                completion_percentage=percentage,
                visited_pages_count=self.visited_pages_count
            )

        async def main():
            global_performance  = await performance()
            urls_performance = await performance_urls()

            self.statistics.update({
                'days': global_performance.days,
                'duration': global_performance.duration,
                'count_urls_to_visit': urls_performance.count_urls_to_visit,
                'count_visited_urls': urls_performance.count_visited_urls
            })
            return global_performance, urls_performance
        return asyncio.run(main())

    def post_navigation_actions(self, current_url, **kwargs):
        """Actions to run on the page just after
        the crawler has visited a page e.g. clicking
        on cookie button banner"""
        pass

    def before_next_page_actions(self, current_url, **kwargs):
        """Actions to run once the page was visited,
        all user actions were performed and just after
        the `wait_time` has expired"""
        pass

    def current_page_actions(self, current_url, **kwargs):
        """Custom actions to execute on the page
        
        >>> def current_page_actions(self, current_url, **kwargs):
        ...     text = self.driver.find_element('h1').text
        """
        pass

    def create_dump(self):
        """Dumps the collected results to a file.
        This functions is called only when an exception
        occurs during the crawling process
        """


class SiteCrawler(BaseCrawler):
    start_url = None

    def __init__(self, browser_name=None):
        super().__init__(browser_name=browser_name)

        self._start_date = get_current_date(timezone=self.timezone)
        self._start_time = time.time()
        self._end_time = None

        self.performance_audit = namedtuple(
            'Performance',
            ['days', 'duration']
        )
        self.urls_audit = namedtuple(
            'URLsAudit',
            ['count_urls_to_visit', 'count_visited_urls',
             'completion_percentage', 'total_urls',
             'visited_pages_count']
        )
        self.statistics = {}

        self.cached_json_items = None
        self.enrichment_mode = False

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass
        logger.info('Project stopped')

    @classmethod
    def create(cls, **params):
        instance = cls(**params)
        return instance

    def before_start(self, start_urls, **kwargs):
        """This function initializes important sections of
        the spider before running `start` function"""
        # To ensure efficient navigation and/or
        # scrapping, use a maximised window since
        # layouts can fundamentally change when
        # using a smaller window
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

            self.list_of_seen_urls.update(*start_urls)
            self.start_url = start_urls.pop()
        self._start_url_object = urlparse(self.start_url)

        # If we have no urls to visit in
        # the array, try to eventually
        # populate the list with existing ones
        if not self.urls_to_visit:
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

    def resume(self, **kwargs):
        """From a previous list of urls to visit
        and visited urls, resume a previous
        crawling session.

            * Redis is checked as the primary database for a cache
            * Memcache is checked in second place
            * Finally, the file cache is used as a final resort
        """
        # redis = backends.redis_connection()
        # if redis:
        #     data = redis.get('cache')
        # else:
        #     memcache = backends.memcache_connection()
        #     if memcache:
        #         data = memcache.get('cache', [])
        #     else:
        #         data = read_json_document('cache.json')
        try:
            data = file_readers.read_json_document('cache.json')
        except FileNotFoundError:
            file_readers.write_json_document('cache.json', [])

        # Before reloading the urls, run the filters
        # in case previous urls to exclude were
        # present
        valid_urls = self.url_filters(data['urls_to_visit'])
        self.urls_to_visit = set(valid_urls)
        self.visited_urls = set(data['visited_urls'])

        try:
            previous_seen_urls = file_readers.read_csv_document(
                'seen_urls.csv',
                flatten=True
            )
        except FileNotFoundError:
            file_readers.write_csv_document('seen_urls.csv', [])
        else:
            self.list_of_seen_urls = set(previous_seen_urls)

        try:
            previous_statistics = file_readers.read_json_document(
                'performance.json'
            )
        except:
            pass
        else:
            self.statistics = previous_statistics

        self.start(**kwargs)

    def start_from_sitemap_xml(self, url, **kwargs):
        """Start crawling from the XML sitemap
        page of a given website

        >>> instance = BaseCrawler()
        ... instance.start_from_html_sitemap("http://example.com/sitemap.xml")
        """
        if not url.endswith('.xml'):
            raise ValueError('Url should point to a sitemap')

        headers = {'User-Agent': RANDOM_USER_AGENT()}
        response = requests.get(url, headers=headers)
        parser = etree.XMLParser(encoding='utf-8')
        xml = etree.fromstring(response.content, parser)

        start_urls = []
        for item in xml.iterchildren():
            sub_children = list(item.iterchildren())
            if not sub_children:
                continue
            start_urls.append(sub_children[0].text)
        return start_urls

    def start_from_html_sitemap(self, url, **kwargs):
        """Start crawling from the sitemap HTML page
        section of a given website

        >>> instance = BaseCrawler()
        ... instance.start_from_html_sitemap("http://example.com/sitemap.html")
        """
        if not 'sitemap' in url:
            raise ValueError('Url should be the sitemap page')

        body = self.driver.find_element(By.TAG_NAME, 'body')
        link_elements = body.find_elements(By.TAG_NAME, 'a')

        urls = []
        for element in link_elements:
            urls.append(element.get_attribute('href'))
        self.start(start_urls=urls, **kwargs)

    def start_from_json(self, windows=0, **kwargs):
        """Enrich a JSON document that with additional
        data by """
        if not isinstance(self._meta.start_urls, LoadStartUrls):
            raise ValueError("start_urls should be an instance of LoadStartUrls")

        # Preload the content to fill
        # the cache
        self.cached_json_items = pandas.read_json(settings.PROJECT_PATH / 'start_urls.json')
        self._meta.crawl = False
        self.enrichment_mode = True

        if windows >= 1:
            self.boost_start(windows=windows, **kwargs)
        else:
            self.start(**kwargs)

    def start(self, start_urls=[], **kwargs):
        """Entrypoint to start the spider

        >>> instance = BaseCrawler()
        ... instance.start(start_urls=["http://example.com"])
        """
        self.before_start(start_urls, **kwargs)

        wait_time = settings.WAIT_TIME

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url is None:
                continue

            current_url_object = urlparse(current_url)
            # If we are not on the same domain as the
            # starting url: *stop*. we are not interested
            # in exploring the whole internet
            if current_url_object.netloc != self._start_url_object.netloc:
                continue

            logger.info(f'Going to url: {current_url}')

            url_instance = URL(current_url)

            # By security measure, do not go to an url
            # that is an image if it happened to be in
            # the urls_to_visit
            if self._meta.ignore_images:
                path = pathlib.Path(current_url_object.path)
                if path.suffix != '':
                    suffix = path.suffix.removeprefix('.')
                    if suffix in constants.IMAGE_EXTENSIONS:
                        continue

            self.driver.get(current_url)
            self.visited_pages_count = self.visited_pages_count + 1

            try:
                # Always wait for the body section of
                # the page to be located  or visible
                wait = WebDriverWait(self.driver, 5)
                wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
            except:
                logger.error('Body element of page was not detected')

            self.post_navigation_actions(url_instance)

            # Post navigation signal
            # TEST: This has to be tested
            # navigation.send(
            #     self,
            #     current_url=current_url,
            #     images_list_filter=['jpg', 'jpeg', 'webp']
            # )

            self.visited_urls.add(current_url)


            if self._meta.crawl:
                # s = time.time()
                self.get_page_urls(url_instance)
                # e = round(time.time() - s, 2)
                # print(f'Completed urls scrap in {e}s')
                self._backup_urls()

            run_action_params = {}

            try:
                if self.enrichment_mode:
                    current_json_object = self.cached_json_items[self.cached_json_items['url'] == current_url]
                    run_action_params.update({'current_json_object': current_json_object})

                # Run custom user actions once
                # everything is completed
                self.current_page_actions(url_instance, **run_action_params)
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
            else:
                # Refresh the urls once the
                # user actions have been completed
                # for example scrolling down a page
                # that could generate new urls to
                # disover or changing a filter
                if self._meta.crawl:
                    self.get_page_urls(url_instance, refresh=True)
                    self._backup_urls()

            # Run routing actions aka, base on given
            # url path, route to a function that
            # would execute said task
            if self._meta.router is not None:
                self._meta.router.resolve(url_instance, self)

            if self._meta.crawl:
                self.calculate_performance()
                file_readers.write_json_document(
                    'performance.json',
                    self.statistics
                )

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

            logger.info(f"Waiting {wait_time}s")
            time.sleep(wait_time)
            self.before_next_page_actions(url_instance)

    def boost_start(self, start_urls=[], *, windows=1, **kwargs):
        """Works just like start but opens multiple windows
        or tabs to accelerate url visitation"""
        self.before_start(start_urls, **kwargs)

        wait_time = settings.WAIT_TIME

        # Create the amount of tabs/windows
        # necessary for visiting each page
        for i in range(windows):
            self.driver.switch_to.new_window('tab')

        # Get position on the first opened window
        # as opposed to the being on the last created one
        self.driver.switch_to.window(self.driver.window_handles[0])

        while self.urls_to_visit:
            current_urls = []

            for _ in self.driver.window_handles:
                try:
                    # In the very start we could have just
                    # one url available to visit. In which
                    # case, just pass. We'll go to the pages
                    # when we get more urls to use in the tabs
                    current_url = self.urls_to_visit.pop()
                except:
                    continue
                else:
                    if current_url is None:
                        continue
                    current_urls.append(current_url)

            logger.info(f"{len(self.urls_to_visit)} urls left to visit")
            url_instances = []

            for i, handle in enumerate(self.driver.window_handles):
                try:
                    # Same. If we only had one url
                    # to start with, this will raise
                    # IndexError - so just skip
                    current_url = current_urls[i]
                except IndexError:
                    continue
                self.driver.switch_to.window(handle)

                current_url_object = urlparse(current_url)
                # If we are not on the same domain as the
                # starting url: *stop*. we are not interested
                # in exploring the whole internet
                if current_url_object.netloc != self._start_url_object.netloc:
                    continue

                logger.info(f'Going to url: {current_url}')

                # By security measure, do not go to an url
                # that is an image if it happened to be in
                # the urls_to_visit
                if self._meta.ignore_images:
                    path = pathlib.Path(current_url_object.path)
                    if path.suffix != '':
                        suffix = path.suffix.removeprefix('.')
                        if suffix in constants.IMAGE_EXTENSIONS:
                            continue

                self.driver.get(current_url)
                self.visited_pages_count = self.visited_pages_count + 1

                try:
                    # Always wait for the body section of
                    # the page to be located  or visible
                    wait = WebDriverWait(self.driver, 5)
                    wait.until(
                        EC.presence_of_element_located((By.TAG_NAME, 'body'))
                    )
                except:
                    logger.error('Body element of page was not detected')

                url_instance = URL(current_url)
                self.post_navigation_actions(url_instance)

                self.visited_urls.add(current_url)
                url_instances.append(url_instance)

            for i, handle in enumerate(self.driver.window_handles):
                try:
                    url_instance = url_instances[i]
                except IndexError:
                    continue
                self.driver.switch_to.window(handle)

                if self._meta.crawl:
                    self.get_page_urls(url_instance)
                    self._backup_urls()
                else:
                    self.visited_urls.add(current_url)
                    self.list_of_seen_urls.add(current_url)
                    self._backup_urls()
                
                try:
                    # Run custom user actions once
                    # everything is completed
                    self.current_page_actions(url_instance)
                except TypeError as e:
                    logger.info(e)
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
                else:
                    # Refresh the urls once the
                    # user actions have been completed
                    # for example scrolling down a page
                    # that could generate new urls to
                    # disover or changing a filter
                    if self._meta.crawl:
                        self.get_page_urls(url_instance, refresh=True)
                        self._backup_urls()

                # Run routing actions aka, base on given
                # url path, route to a function that
                # would execute said task
                if self._meta.router is not None:
                    self._meta.router.resolve(url_instance, self)

                if self._meta.crawl:
                    self.calculate_performance()
                    file_readers.write_json_document(
                        'performance.json', 
                        self.statistics
                    )

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

            current_urls.clear()
            url_instances.clear()

            logger.info(f"Waiting {wait_time}s")
            time.sleep(wait_time)


class JSONCrawler:
    """Crawl the data of an API endpoint by retrieving
    the data given an interval in minutes"""

    base_url = None
    received_data = []
    date_sorted_data = defaultdict(list)
    iterator = AsyncIterator

    def __init__(self, chunks=10):
        self.chunks = chunks
        self.request_sent = 0

        self.max_pages = 0
        self.current_page_key = None
        self.current_page = 1
        self.max_pages_key = None
        self.paginate_data = False
        self.pagination = 0
        self.current_raw_data = {}

        if self.base_url is None:
            raise ValueError("'base_url' cannot be None")

        self._url = URL(self.base_url)

    @property
    def data(self):
        return self.iterator(self.received_data, by=self.chunks)

    async def create_dump(self):
        pass

    async def clean(self, data):
        """Use this function to run additional logic
        on the retrieved data"""
        return pandas.DataFrame(data)

    async def start(self, interval=15):
        logger.info(f'Starting {self.__class__.__name__}')
        logger.info(f'A request will be made every {interval} minutes')

        session = Session()
        request = Request(
            method='get',
            url=str(self._url),
            headers={'Content-Type': 'application/json'},
            auth=None
        )
        prepared_request = session.prepare_request(request)

        interval = datetime.timedelta(minutes=interval)
        time_interval = (0, 0)

        queue = asyncio.Queue()

        async def receiver():
            webhooks = Webhooks(settings.STORAGE_BACKENDS['webhooks'])
            while True:
                while not queue.empty():
                    data = await queue.get()

                    self.received_data.extend(data)
                    self.date_sorted_data[str(get_current_date())] = data
                    await webhooks.resolve(data)

                    await asyncio.sleep(5)
                await asyncio.sleep(15)

        async def sender():
            next_date = get_current_date() + interval
            time_until_next_execution = 0
            while True:
                current_date = get_current_date()

                # start_time, end_time = time_interval
                time_until_next_execution = (
                    next_date - current_date
                ).total_seconds()

                if time_until_next_execution <= 0:
                    start_time = time.time()

                    # Some endpoints allow pagination
                    # of the data in order to get additional
                    # items. So updat the pagination number
                    # on the url
                    if self.paginate_data:
                        if self.pagination == 0:
                            self.pagination = self.pagination + 1
                            continue

                        page = self.pagination + 1
                        if page > self.max_pages:
                            page = 0

                    try:
                        response = session.send(prepared_request)
                    except:
                        logger.error('Request failed')
                    else:
                        if response.ok:
                            logger.info('Request successfully completed')
                            try:
                                self.current_raw_data = response.json()
                            except requests.exceptions.JSONDecodeError as e:
                                logger.error(
                                    f"Could not decode content as JSON "
                                    "got: {response.content[:50]} - {e}"
                                )
                            else:
                                data_or_dataframe = await self.clean(self.current_raw_data)
                                if isinstance(data_or_dataframe, pandas.DataFrame):
                                    data = data_or_dataframe.to_json(
                                        orient='records',
                                        force_ascii=False
                                    )
                                else:
                                    data = data_or_dataframe

                                logger.info(
                                    f"Received {len(self.current_raw_data)} elements"
                                )

                                if self.paginate_data:
                                    self.max_pages = data[self.max_pages_key]
                                    self.current_page = data[self.current_page]

                                await queue.put(data)

                    end_time = round(time.time() - start_time, 1)
                    next_date = next_date + interval
                    self.request_sent = self.request_sent + 1
                    self.current_raw_data = {}

                    logger.info(f'Request completed in {end_time}s')

                await asyncio.sleep(60)

        await asyncio.gather(sender(), receiver())
