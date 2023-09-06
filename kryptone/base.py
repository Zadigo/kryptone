import bisect
import datetime
import json
import random
import re
import string
import asyncio
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
from kryptone import exceptions
from kryptone.signals import Signal
from kryptone.utils import file_readers
from kryptone.utils.file_readers import (read_csv_document, read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.iterators import JPEGImagesIterator
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL, URLPassesTest
from kryptone.utils.file_readers import URLCache

WEBDRIVER_ENVIRONMENT_PATH = 'KRYPTONE_WEBDRIVER'

DEFAULT_META_OPTIONS = {
    'domains', 'audit_page', 'url_passes_tests',
    'debug_mode', 'site_language', 'default_scroll_step',
    'gather_emails', 'router', 'crawl'
}


# post_init = Signal()
navigation = Signal()
db_signal = Signal()


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
        # cache.extend_list('images', instance.urls)


def get_selenium_browser_instance(browser_name=None):
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
    options.add_argument(f'user-agent={RANDOM_USER_AGENT()}')

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
        self.audit_page = False
        self.url_passes_tests = None
        self.debug_mode = False
        self.site_language = 'en'
        self.default_scroll_step = 80
        self.gather_emails = False
        self.router = None
        self.crawl = True

    def __repr__(self):
        return f'<{self.__class__.__name__} for {self.verbose_name}>'

    def add_meta_options(self, options):
        for name, value in options:
            if name not in DEFAULT_META_OPTIONS:
                raise ValueError(
                    "Meta for model '{name}' received "
                    "an illegal option '{option}'".format(
                        name=self.verbose_name,
                        option=name
                    )
                )
            setattr(self, name, value)

    def prepare(self):
        pass
        # for option in DEFAULT_META_OPTIONS:
        #     if not hasattr(self, option):
        #         if option in ['domains', 'url_passes_tests']:
        #             setattr(self, option, [])

        #         if option in ['audit_page', 'gather_emails', 'debug_mode']:
        #             setattr(self, option, False)

        #         if option == 'site_language':
        #             setattr(self, option, None)

        #         if option == 'default_scroll_step':
        #             setattr(self, 'default_scroll_step', 80)


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
    list_of_seen_urls = set()
    browser_name = None
    debug_mode = False
    timezone = 'UTC'
    default_scroll_step = 80

    def __init__(self, browser_name=None):
        self._start_url_object = None
        self.driver = get_selenium_browser_instance(
            browser_name=browser_name or self.browser_name
        )

        # navigation.connect(collect_images_receiver, sender=self)

        # db_signal.connect(backends.airtable_backend, sender=self)
        # db_signal.connect(backends.notion_backend, sender=self)
        # db_signal.connect(backends.google_sheets_backend, sender=self)

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
        return self.driver.find_elements(By.TAG_NAME, 'a')

    @property
    def get_title_element(self):
        return self.driver.find_element(By.TAG_NAME, 'title')

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

        sorted_urls = []
        for url in self.list_of_seen_urls:
            bisect.insort(sorted_urls, url)
        write_csv_document('seen_urls.csv', sorted_urls, adapt_data=True)
        # db_signal.send(
        #     self,
        #     data_type='urls',
        #     urls_data=urls_data
        # )

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

    def create_filename(self, length=5, extension=None):
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
        logger.info(f'{len(urls_or_paths)} added')

    def get_page_urls(self):
        """Returns all the urls present on the
        actual given page"""
        elements = self.get_page_link_elements
        logger.info(f"Found {len(elements)} urls")

        for element in elements:
            link = element.get_attribute('href')

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
                # link = f'{self._start_url_object.scheme}://{self._start_url_object.netloc}{link}'
                link = urlunparse((
                    self._start_url_object.scheme,
                    self._start_url_object.netloc,
                    link,
                    None,
                    None,
                    None
                ))

            self.urls_to_visit.add(link)

            # For statistics, we'll keep track of all the
            # urls that we have gathered during crawl
            self.list_of_seen_urls.add(link)

        # Finally, run all the filters to exclude
        # urls that the user does not want to visit
        # from the list of urls. NOTE: This re-initializes
        # the list of urls to visit
        # previous_state = self.urls_to_visit.copy()
        self.urls_to_visit = set(self.run_filters())
        # excluded_urls = previous_state.difference(self.urls_to_visit)
        # logger.info(f'Ignored {len(excluded_urls)} urls')

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
        script = """
        const result = document.evaluate('{path}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
        return result.singleNodeValue
        """.format(path=path)
        return self.driver.execute_script(script)

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
        """Returns the amount of time for which the
        spider has been running"""
        self._end_date = self.get_current_date()
        days = (self._start_date - self._end_date).days
        completed_time = round(time.time() - self._start_time, 1)
        days = 0 if days < 0 else days
        return self.performance_audit(days, completed_time)

    def calculate_completion_percentage(self):
        """Indicates the level of completion
        for the current crawl session"""
        total_urls = sum([len(self.visited_urls), len(self.urls_to_visit)])
        result = len(self.visited_urls) / total_urls
        percentage = round(result, 5)
        logger.info(f'{percentage * 100}% of total urls visited')

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

    def __init__(self, browser_name=None):
        super().__init__(browser_name=browser_name)
        self._start_date = self.get_current_date()

        self._start_time = time.time()
        self._end_time = None
        self.performance_audit = namedtuple(
            'Performance', ['days', 'duration']
        )

        self.statistics = {}

    def update_statistics(self):
        current_date = self.get_current_date().date()
        self.date_history[current_date] = self.date_history[current_date] + 1

    def resume(self, **kwargs):
        """From a previous list of urls to visit
        and visited urls, resume a previous
        crawling session.

            * Redis is checked as the primary database for a cache
            * Memcache is checked afterwards if no connection
            * Finally, the file cache is used as a final resort
        """
        redis = redis_connection()
        if redis:
            data = redis.get('cache')
        else:
            memcache = memcache_connection()
            if memcache:
                data = memcache.get('cache', [])
            else:
                data = read_json_document('cache.json')

        self.urls_to_visit = set(data['urls_to_visit'])
        self.visited_urls = set(data['visited_urls'])
        self.list_of_seen_urls = set(
            read_csv_document('seen_urls.csv', flatten=True))
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
        # self.start(start_urls=start_urls, **kwargs)

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

    def start(self, start_urls=[], **kwargs):
        """Entrypoint to start the spider

        >>> instance = BaseCrawler()
        ... instance.start(start_urls=["http://example.com"])
        """
        # To ensure efficient navigation and/or
        # scrapping, use a maximised window since
        # layouts can fundamentally change when
        # using a smaller window
        logger.info(f'{self.__class__.__name__} ready to crawl website')
        self.driver.maximize_window()

        wait_time = settings.WAIT_TIME

        if self._meta.debug_mode:
            logger.info('Starting Kryptone in debug mode...')
        else:
            logger.info('Starting Kryptone...')

        if isinstance(start_urls, URLCache):
            self.urls_to_visit = start_urls.urls_to_visit
            self.visited_urls = start_urls.visited_urls

        if self.start_url is None:
            raise ValueError('A starting url should be provided to the spider')

        # If we have no urls to visit in
        # the array, try to eventually
        # populate the list with existing ones
        if not self.urls_to_visit:
            # Start spider from .xml page
            is_xml_page = self.start_url.endswith('.xml')
            if not is_xml_page:
                # Add the start_url to the list of
                # urls to visit - as entrypoint
                self.add_urls(self.start_url)
            else:
                start_urls = self.start_from_sitemap_xml(self.start_url)
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
            self.driver.get(current_url)

            # Always wait for the body section of
            # the page to be located  or visible
            wait = WebDriverWait(self.driver, 8)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            self.post_visit_actions(current_url=current_url)

            # Post navigation signal
            # TEST: This has to be tested
            # navigation.send(
            #     self,
            #     current_url=current_url,
            #     images_list_filter=['jpg', 'jpeg', 'webp']
            # )

            self.visited_urls.add(current_url)

            # TODO: Check performance issues here
            if self._meta.crawl:
                self.get_page_urls()
                self._backup_urls()

            if self._meta.audit_page:
                self.audit_page(current_url)
                write_json_document('audit.json', self.page_audits)

                # Write vocabulary as JSON
                vocabulary = self.global_audit()
                write_json_document('global_audit.json', vocabulary)

                # Write vocabulary as CSV
                rows = []
                for key, value in vocabulary.items():
                    rows.append([key, value])
                write_csv_document('global_audit.csv', rows)

                # Save the website's text
                website_text = ' '.join(self.fitted_page_documents)
                file_readers.write_text_document('website.txt', website_text)

                # cache.set_value('page_audit', self.page_audits)
                # cache.set_value('global_audit', vocabulary)
                db_signal.send(
                    self,
                    page_audit=self.page_audits,
                    global_audit=vocabulary
                )

                logger.info('Audit complete...')

            if self._meta.gather_emails:
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
            url_instance = URL(current_url)
            try:
                self.run_actions(url_instance)
            except TypeError:
                raise TypeError("run_actions should accept arguments")
            except Exception:
                ExceptionGroup('An exception occured while trying to run user actions', [
                    exceptions.SpiderExecutionError()
                ])

            # Run routing actions aka, base on given
            # url path, route to a function that
            # would execute said task
            if self._meta.router is not None:
                self._meta.router.resolve(current_url, self)

            if self._meta.crawl:
                performance = self.calculate_performance()
                self.calculate_completion_percentage()

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            logger.info(f"Waiting {wait_time}s")
            time.sleep(wait_time)


class AsyncWebCrawler(SiteCrawler):
    async def astart(self, start_urls=[], **kwargs):
        current_url = None
        urls_queue = asyncio.Queue()

        wait_time = settings.WAIT_TIME

        async def url_collector():
            while True:
                if current_url is None:
                    self.get_page_urls()
                    current_url = self.driver.current_url
                    for url in self.urls_to_visit:
                        await urls_queue.put(url)
                    continue

                if current_url != self.driver.current_url:
                    self.get_page_urls()

                    for url in self.urls_to_visit:
                        await urls_queue.put(url)

                await asyncio.sleep(1)

        async def web_scrapper():
            while not urls_queue.empty():
                current_url = await urls_queue.get()
                self.driver.get(current_url)

                if settings.WAIT_TIME_RANGE:
                    start = settings.WAIT_TIME_RANGE[0]
                    stop = settings.WAIT_TIME_RANGE[1]
                    wait_time = random.randrange(start, stop)
                asyncio.sleep(wait_time)

        asyncio.gather(web_scrapper(), url_collector())


crawler = AsyncWebCrawler(browser_name='Edge')
asyncio.run(crawler.astart(start_urls=['http://example.com']))
