import asyncio
import bisect
import datetime
import os
import random
import time
from collections import defaultdict, namedtuple
from functools import cached_property
from urllib.parse import unquote, urlparse, urlunparse
from selenium.webdriver.common.proxy import Proxy, ProxyType
import pandas
import pytz
import requests
from lxml import etree
from requests import Session
from requests.models import Request
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import exceptions, logger
from kryptone.conf import settings
from kryptone.db import backends
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.utils import file_readers
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.file_readers import (LoadStartUrls, read_csv_document,
                                         read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.iterators import AsyncIterator
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL, URLGenerator, pathlib
from kryptone import constants
from kryptone.webhooks import Webhooks
from kryptone import exceptions

DEFAULT_META_OPTIONS = {
    'domains', 'audit_page', 'url_passes_tests',
    'debug_mode', 'site_language', 'default_scroll_step',
    'gather_emails', 'router', 'crawl', 'start_urls',
    'ignore_queries', 'ignore_images', 'restrict_search_to'
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
    if settings.USE_PROXY_ADDRESS:
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
        self.audit_page = False
        self.url_passes_tests = None
        self.debug_mode = False
        self.site_language = 'en'
        self.default_scroll_step = 80
        self.gather_emails = False
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
    debug_mode = False
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
                        f"Found {len(urls)} url(s) in '{selector}'")
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
            self._start_url_object.path,
            None,
            None,
            None
        ))

    def _backup_urls(self):
        """Backs up the urls both in memory 
        and file cache which can then be resumed
        on a next run"""
        d = get_current_date(timezone=self.timezone)

        urls_data = {
            'spider': self.__class__.__name__,
            'timestamp': d.strftime('%Y-%M-%d %H:%M:%S'),
            'urls_to_visit': list(self.urls_to_visit),
            'visited_urls': list(self.visited_urls)
        }

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

    def run_filters(self):
        """Excludes urls in the list of urls to visit based
        on the return value of the function in `url_filters`.
        All conditions should be true for the url to be
        considered to be visited.
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
            message = (
                f"Url filter completed. {len(filtered_urls)} "
                "successfully passed the tests"
            )
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
            new_url_object = urlparse(new_url)

            if item.startswith('/'):
                new_url = urlunparse((
                    self._start_url_object.scheme,
                    self._start_url_object.netloc,
                    item,
                    None,
                    None,
                    None
                ))

            if new_url_object.netloc == '' and new_url_object.path == '':
                continue

            if new_url_object.netloc != self._start_url_object.netloc:
                continue

            if new_url in self.visited_urls:
                continue

            if new_url in self.urls_to_visit:
                continue

            self.urls_to_visit.add(new_url)
        logger.info(f'{len(urls_or_paths)} url(s) added')

    def get_page_urls(self):
        """Returns all the urls present on the
        actual given page"""
        links = self.get_page_link_elements
        logger.info(f"Found {len(links)} url(s) on this page")

        for link in links:
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
            # repetition. Additionally this is a
            # guard against http://example.com# from
            # urlparse which does not detect the #
            if link.endswith('#'):
                continue

            # If the link is similar to the initially
            # visited url, skip it.
            # NOTE: This is essentially a  security measure
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
                link = urlunparse((
                    self._start_url_object.scheme,
                    self._start_url_object.netloc,
                    link,
                    None,
                    None,
                    None
                ))

            if self._meta.ignore_queries:
                if link_object.query != '':
                    continue

            if self._meta.ignore_images:
                path = pathlib.Path(link_object.path)
                if path.suffix != '':
                    suffix = path.suffix.removeprefix('.')
                    if suffix in constants.IMAGE_EXTENSIONS:
                        continue

            self.urls_to_visit.add(link)

        # Finally, run all the filters to exclude
        # urls that the user does not want to visit
        # NOTE: This re-initializes the list of
        # urls to visit
        self.urls_to_visit = set(self.run_filters())

        newly_discovered_urls = []
        for link in links:
            if link not in self.list_of_seen_urls:
                newly_discovered_urls.append(link)

            # For statistics, we'll keep track of all the
            # urls that we have gathered during crawl
            self.list_of_seen_urls.add(link)

        if newly_discovered_urls:
            logger.info(
                f"Disovered {len(newly_discovered_urls)} "
                "new overall url(s)"
            )

    def refresh_page_urls(self):
        """This function will only check if urls
        were registered in the list of urls that
        were already seen (regardless of the page).
        This function should be used only to compare a
        new incoming list of urls to seen ones

        The filtering here is less more strict than `get_page_urls`
        since we are interested in ALL urls that were *potentially*
        seen to be visitable
        """
        newly_discovered_urls = []
        for url in self.get_page_link_elements:
            # url_object = urlparse(url)

            # if new_url_object.netloc == '' and new_url_object.path == '':
            #     continue

            # if url_object.path != '/' and url.startswith('/'):
            #     url = urlunparse((
            #         self._start_url_object.scheme,
            #         self._start_url_object.netloc,
            #         url,
            #         None,
            #         None,
            #         None
            #     ))

            # if url in self.list_of_seen_urls:
            #     continue
            
            newly_discovered_urls.append(url)
            self.list_of_seen_urls.add(url)
        self.add_urls(*newly_discovered_urls)

        if newly_discovered_urls:
            logger.info(
                f"Got {len(newly_discovered_urls)} new url(s) "
                "after url discovery refresh"
            )
        self.add_urls(*newly_discovered_urls)

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
        self._end_date = get_current_date(timezone=self.timezone)
        days = (self._start_date - self._end_date).days
        completed_time = round(time.time() - self._start_time, 1)
        days = 0 if days < 0 else days
        global_performance = self.performance_audit(days, completed_time)

        # Calculate performance related to urls
        total_urls = sum([len(self.visited_urls), len(self.urls_to_visit)])
        result = len(self.visited_urls) / total_urls
        percentage = round(result * 100, 3)
        logger.info(f'{percentage}% of total urls visited')

        urls_performance = self.urls_audit(
            count_urls_to_visit=len(self.urls_to_visit),
            count_visited_urls=len(self.visited_urls),
            total_urls=total_urls,
            completion_percentage=percentage,
            visited_pages_count=self.visited_pages_count
        )

        self.statistics.update({
            'days': global_performance.days,
            'duration': global_performance.duration,
            'count_urls_to_visit': urls_performance.count_urls_to_visit,
            'count_visited_urls': urls_performance.count_visited_urls
        })
        return global_performance, urls_performance

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

    def __del__(self):
        self.driver.quit()
        logger.info('Project stopped')

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
        data = read_json_document('cache.json')
        self.urls_to_visit = set(data['urls_to_visit'])
        self.visited_urls = set(data['visited_urls'])

        previous_seen_urls = read_csv_document('seen_urls.csv', flatten=True)
        self.list_of_seen_urls = set(previous_seen_urls)
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

        start_urls = start_urls or self._meta.start_urls

        # If we have absolutely no start_url and at the
        # same time we have no start_urls, raise an error
        if self.start_url is None and not start_urls:
            raise exceptions.BadImplementationError(
                "No start url. Provide either a "
                "start url or start urls in the Meta"
            )

        if self.start_url is None and start_urls:
            if isinstance(start_urls, (LoadStartUrls)):
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
        self._start_url_object = urlparse(self.start_url)

        if start_urls:
            self.add_urls(*start_urls)

        # webhooks = Webhooks(settings.STORAGE_BACKENDS['webhooks'])

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url is None:
                continue

            # In the case where the user has provided a
            # set of urls directly in the function,
            # start_url would be None
            # if self.start_url is None:
            #     self.start_url = current_url
            #     self._start_url_object = urlparse(self.start_url)

            current_url_object = urlparse(current_url)
            # If we are not on the same domain as the
            # starting url: *stop*. we are not interested
            # in exploring the whole internet
            if current_url_object.netloc != self._start_url_object.netloc:
                continue

            logger.info(f'Going to url: {current_url}')
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

            self.post_visit_actions(current_url=current_url)

            # Post navigation signal
            # TEST: This has to be tested
            # navigation.send(
            #     self,
            #     current_url=current_url,
            #     images_list_filter=['jpg', 'jpeg', 'webp']
            # )

            self.visited_urls.add(current_url)

            url_instance = URL(current_url)

            if self._meta.crawl:
                # s = time.time()
                self.get_page_urls()
                # e = round(time.time() - s, 2)
                # print(f'Completed urls scrap in {e}s')
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
                file_readers.write_text_document(
                    'website_text.txt', website_text)

                # cache.set_value('page_audit', self.page_audits)
                # cache.set_value('global_audit', vocabulary)
                # db_signal.send(
                #     self,
                #     page_audit=self.page_audits,
                #     global_audit=vocabulary
                # )

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
                # db_signal.send(
                #     self,
                #     emails=self.emails_container
                # )

            try:
                # Run custom user actions once
                # everything is completed
                self.run_actions(url_instance)
            except TypeError:
                raise TypeError(
                    "'self.run_actions' should be able to accept arguments"
                )
            except Exception as e:
                logger.error(e)
                raise ExceptionGroup(
                    "An exception occured while trying "
                    "to execute 'self.run_actions'",
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
                    self.refresh_page_urls()
                    self._backup_urls()

            # Run routing actions aka, base on given
            # url path, route to a function that
            # would execute said task
            if self._meta.router is not None:
                self._meta.router.resolve(url_instance, self)

            if self._meta.crawl:
                self.calculate_performance()
                write_json_document('performance.json', self.statistics)

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

            logger.info(f"Waiting {wait_time}s")
            time.sleep(wait_time)


class JSONCrawler:
    """Crawl the data of an API endpoint by retrieving
    the data given an interval in minutes"""

    base_url = None
    receveived_data = []
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

        if self.base_url is None:
            raise ValueError("'base_url' cannot be None")

        self._url = URL(self.base_url)

    @property
    def data(self):
        return self.iterator(self.receveived_data, by=self.chunks)

    async def clean(self, dataframe):
        """Use this function to run additional logic
        on the retrieved data"""
        return dataframe.to_json()

    async def start(self, interval=15):
        logger.info('Starting JSON crawler')

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
                    # self.receveived_data.extend(data)
                    # await webhooks.resolve(data)
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
                        df = pandas.DataFrame(data=response.json())
                        data_or_dataframe = await self.clean(df)
                        if isinstance(data_or_dataframe, pandas.DataFrame):
                            data = data_or_dataframe.to_json(
                                orient='records', force_ascii=False)
                        else:
                            data = data_or_dataframe

                        if self.paginate_data:
                            self.max_pages = data[self.max_pages_key]
                            self.current_page = data[self.current_page]

                        end_time = round(time.time() - start_time, 1)
                        await queue.put(data)

                    next_date = next_date + interval
                    self.request_sent = self.request_sent + 1

                    logger.info(f'Request completed in {end_time}s')

                await asyncio.sleep(60)

        await asyncio.gather(sender(), receiver())
