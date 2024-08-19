import dataclasses
import datetime
import pathlib
import time
from collections import defaultdict
from dataclasses import dataclass, field, is_dataclass
from urllib.parse import unquote, urlparse, urlunparse

import pandas
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.proxy import Proxy, ProxyType
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import logger
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
    container = None
    saved_data = None

    def __init__(self, browser_name=None, debug=False, after_seconds=None):
        self.browser_name = browser_name
        self.after_seconds = after_seconds
        self.driver = None
        self.debug = debug
        self.start_url_object = None

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

        self.performance = Performance()

    def __repr__(self):
        name = self.__class__.__new__()
        return f'<{name}:>'

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
    def get_current_date(self):
        return datetime.datetime.now()

    @property
    def get_origin(self):
        return urlunparse((
            self.start_url_object.scheme,
            self.start_url_object.netloc,
            None,
            None,
            None,
            None
        ))

    @property
    def get_page_link_elements(self):
        """Property that returns all the links on a
        given page or on the specific section e.g.
        body, section..."""
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
        return self.check_urls(found_urls)

    @staticmethod
    def urljoin(self, path):
        """Returns the domain of the current
        website"""
        path = str(path).strip()
        result = urlunparse((
            self.start_url_object.scheme,
            self.start_url_object.netloc,
            path,
            None,
            None,
            None
        ))
        return unquote(result)

    def url_structural_check(self, url):
        """Checks that the url is a path
        or with http/https"""
        if str(url).startswith('/'):
            return URL(self.urljoin(str(url)))
        return URL(url)

    def create_dataframe_from_urls(self, urls=[]):
        local_df = pandas.DataFrame({'urls': urls})
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

        local_df = local_df[~local_df.duplicated()]

        local_df['ignore'] = False

        def url_gather_ignore_tests(df):
            return df

        def url_basic_check_test(df):
            if self._meta.url_gather_ignore_tests:
                for item in df.itertuples():
                    url_instance = URL(item.urls)

                    if item.ignore:
                        continue

                    if not url_instance.is_same_domain(self.start_url_object):
                        df.loc[item.Index, 'ignore'] = True
                        continue

                    if url_instance.is_empty:
                        df.loc[item.Index, 'ignore'] = True
                        continue

                    if url_instance.has_fragment:
                        df.loc[item.Index, 'ignore'] = True
                        continue

                    if (url_instance.url_object.path == '/' and
                            self.start_url_object.url_object.path == '/'):
                        df.loc[item.Index, 'ignore'] = True
                        continue

                    if self._meta.ignore_queries:
                        if url_instance.has_queries():
                            df.loc[item.Index, 'ignore'] = True
                            continue

                    if self._meta.ignore_images:
                        if url_instance.is_image:
                            df.loc[item.Index, 'ignore'] = True
                            continue
            return df

        local_df.pipe(url_basic_check_test)

        return local_df

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

        * Check that the url was not already seen and therefore
          invalid be navigated to"""
        if isinstance(list_or_dataframe, (list, set)):
            list_or_dataframe = self.create_dataframe_from_urls(
                urls=list_or_dataframe
            )

        # 1. Check that the urls that we are trying to add
        # do not already exist in the database of seen urls
        unseen_urls_df = list_or_dataframe.isin(
            {'urls': self.seen_urls.urls.tolist()})
        unseen_urls = list_or_dataframe[unseen_urls_df.urls == False]

        self.seen_urls = pandas.concat(
            [
                self.seen_urls,
                unseen_urls[['urls']]
            ]
        )
        self.seen_urls.sort_values('urls')

        if unseen_urls.urls.count() > 0:
            final_df = self.check_urls(unseen_urls)
            logger.info(f'Added {final_df.urls.count()} more urls to visit')

            self.merge_urls(final_df)

    def before_page_actions(self, url, *args, **kwargs):
        return NotImplemented

    def current_page_actions(self, url, *args, **kwargs):
        return NotImplemented

    def on_error(self, url, message, *args, **kwargs):
        self.urls_to_visit.loc[
            self.urls_to_visit.urls == url,
            'error'
        ] = message
        self.urls_to_visit.to_csv('visited_urls.csv', index_label='id')

    def before_next_page_actions(self, url, *args, **kwargs):
        self.urls_to_visit.to_csv('visited_urls.csv', index_label='id')

    def after_data_save(self, dataframe):
        return NotImplemented

    def before_start(self):
        logger.info(f'{self.__class__.__name__} ready to crawl website')

        if self._meta.debug_mode:
            logger.info('Starting Kryptone in debug mode...')
        else:
            logger.info('Starting Kryptone...')

    def start(self, start_urls=[], filename=None, sort_data_by=None):
        self.before_start()

        if filename is not None:
            self.load_file(filename)

        if start_urls:
            self.add_urls(start_urls)

        if self.after_seconds is not None:
            time.sleep(self.after_seconds)

        next_execution_date = None
        while self.urls_to_visit_list:
            if next_execution_date is not None:
                if self.get_current_date < next_execution_date:
                    continue

            current_url = URL(self.urls_to_visit_list.pop())
            if self.start_url_object is None:
                self.start_url_object = current_url

            item = self.urls_to_visit.loc[self.urls_to_visit.urls == current_url]
            self.before_page_actions(current_url)

            try:
                if self.debug:
                    logger.debug('Kryptone is running debug mode')
                else:
                    self.driver.get(str(current_url))
            except Exception as e:
                self.performance.add_error_count()
                self.on_error(current_url, e.args)
                continue

            if not self._meta.debug_mode:
                if self._meta.crawl:
                    new_urls_df = self.check_urls(self.get_page_link_elements)
                    self.add_urls(new_urls_df)

            logger.info(f'Going to url: {current_url}')

            self.urls_to_visit.loc[item.index, 'visited'] = True
            self.urls_to_visit.loc[
                item.index, 'date'] = self.get_current_date

            data = self.current_page_actions(current_url)
            if data is not None:
                if isinstance(data, list):
                    local_df = pandas.DataFrame(data)
                    self.saved_data = pandas.concat(
                        [
                            local_df,
                            self.saved_data
                        ]
                    )

                    if sort_data_by is not None:
                        self.saved_data.sort_values(sort_data_by)

                    self.after_data_save(self.saved_data)

            self.before_next_page_actions(current_url)

            next_execution_date = (
                self.get_current_date +
                datetime.timedelta(seconds=5)
            )

            self.performance.add_iteration_count()

            if len(self.urls_to_visit_list) == 0:
                self.performance.end_date = self.get_current_date
                self.performance.calculate_duration()


class SiteCrawler(BaseCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# crawler = SiteCrawler(
#     browser_name='Edge',
#     debug=True
# )
# crawler.start(
#     filename='start_urls.csv',
#     urls_to_visit=[
#         'http://example.com/1',
#         'http://example.com/2'
#     ]
# )

class Custom(SiteCrawler):
    class Meta:
        debug_mode = True
        crawl = True


c = Custom(browser_name='Edge', debug=True)
c.start(
    # filename='start_urls.csv',
    start_urls=[
        'http://example.com/1',
        'http://example.com/2'
    ]
)
