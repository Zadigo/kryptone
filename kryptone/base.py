import asyncio
import bisect
import dataclasses
import datetime
import inspect
import io
import os
import pathlib
import random
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import unquote, urljoin, urlunparse
from uuid import uuid4

import pytz
import requests
from asgiref.sync import async_to_sync
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import exceptions, logger, signal_constants
from kryptone.conf import settings
from kryptone.data_storages import BaseStorage, FileStorage
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.functions import create_filename, directory_from_url
from kryptone.utils.module_loaders import import_from_module
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.text import color_text
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

    try:
        service = Service(manager_instance().install())
    except Exception:
        raise ConnectionError('And error occured. Are you offline?')
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
        default_factory=lambda: datetime.datetime.now(tz=pytz.UTC)
    )
    end_date: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(tz=pytz.UTC)
    )
    timezone: str = 'UTC'
    error_count: int = 0
    duration: int = 0
    count_urls_to_visit: int = 0
    count_visited_urls: int = 0

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

    def load_statistics(self, data):
        self.iteration_count = data['iteration_count']

        date_format = '%Y-%m-%dT%H:%M:%S.%f'
        self.start_date = datetime.datetime.strptime(
            data['start_date'],
            date_format
        )
        self.start_date.replace(tzinfo=pytz.timezone(data['timezone']))

        self.count_urls_to_visit = data.get('count_urls_to_visit', 0)
        self.count_visited_urls = data.get('count_visited_urls', 0)

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
        # The start url which corresponds
        # to the first url of "Meta.start_urls"
        # allows us to track the domain to which
        # crawling needs to be limited to
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

    def download_images(self, urls, page_url, directory=None, exclude_paths=[], filename_attrs={}):
        """A method that can be called with a list of image urls to download. The
        images will be stored the indicated media folder"""
        if not isinstance(urls, list):
            return False

        try:
            from PIL import Image
        except:
            return False

        async def save_image(url, img):
            qualified_directory = None
            if directory is None:
                # Use the default url structure to determine
                # the actual directory structure for the image
                qualified_directory = directory_from_url(
                    page_url,
                    exclude=exclude_paths
                )
            else:
                if isinstance(directory, str):
                    qualified_directory = pathlib.Path(directory)
                else:
                    qualified_directory = directory

            qualified_directory = settings.MEDIA_FOLDER.joinpath(
                qualified_directory
            )
            if not qualified_directory.exists():
                qualified_directory.mkdir()

            inferred_filename = url.get_filename
            if inferred_filename is None:
                logger.warning(
                    color_text(
                        'yellow',
                        "File name could not be infered "
                        "from url. Using random characters"
                    )
                )
                filename_attrs.update(suffix_with_date=True)
                inferred_filename = create_filename(**filename_attrs)
            else:
                name, extension = inferred_filename.split('.')
                if 'suffix' not in filename_attrs:
                    filename_attrs.update(suffix=name)
                filename_attrs.update(extension=extension)
                inferred_filename = create_filename(**filename_attrs)

            filepath = qualified_directory.joinpath(inferred_filename)

            pil_extension = 'JPEG'
            if url.get_extension == '.png':
                pil_extension = 'PNG'

            try:
                img.save(filepath, format=pil_extension)
            except Exception as e:
                logger.error(e)
            else:
                logger.info(f"Downloaded image: {url}")

        async def image_reader(url, buffer):
            img = Image.open(buffer)
            refactored_img = None

            # image_data = img.getdata()
            resize = getattr(settings, 'IMAGE_DOWNLOAD_RESIZE', ())
            if resize:
                if len(resize) < 1:
                    raise ValueError('Resize should be a tuple of two values')

                resize = list(resize)
                dimensions = (img.width // resize[0], img.height // resize[1])
                refactored_img = img.resize(dimensions)

            if refactored_img is None:
                refactored_img = img

            await save_image(url, refactored_img)
            return refactored_img

        async def downloader(task_group, url):
            try:
                response = requests.get(url)
            except:
                logger.warning(f"Could not download image: {color_text('red', url)}")
                return False
            else:
                if response.status_code == 200:
                    buffer = io.BytesIO(response.content)
                    await task_group.create_task(image_reader(URL(url), buffer))

        async def main():
            tasks = []

            async with asyncio.TaskGroup() as tg:
                for url in urls:
                    task = tg.create_task(downloader(tg, url))
                    tasks.append(task)
                await asyncio.gather(*tasks)

        asyncio.run(main())
        self.storage.initialize()

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
                        getattr(instance, field.name)
                    )
                    setattr(instance, field.name, result)

            for check_field in check_fields_null:
                if getattr(instance, check_field) is None:
                    continue

            logger.info(f'Saving: {instance}')
            self.DATA_CONTAINER.append(instance)

    def backup_urls(self):
        if self.storage is None:
            self.storage = FileStorage(
                spider=self,
                storage_path=settings.MEDIA_FOLDER
            )

        async def run_additional_storages(key, value):
            for name, storage in self.additional_storages:
                # Only use storages that are connected.
                # This is a none block loop
                if not storage.is_connected:
                    logger.warning(
                        f"Could not use {name}. "
                        "Connection broken"
                    )
                    continue
                await storage.save_or_create(key, value)

        async def write_cache_file():
            data = {
                'spider': self.__class__.__name__,
                'spider_uuid': self.spider_uuid,
                'timestamp': self.get_current_date.strftime('%Y-%M-%d %H:%M:%S'),
                'urls_to_visit': self.urls_to_visit,
                'visited_urls': self.visited_urls
            }

            key_or_filename = f'{settings.CACHE_FILE_NAME}.json'
            await self.storage.save_or_create(key_or_filename, data)
            await run_additional_storages(key_or_filename, data)

        async def write_seen_urls():
            sorted_urls = []
            for url in self.list_of_seen_urls:
                bisect.insort(sorted_urls, url)

            key_or_filename = 'seen_urls.csv'
            await self.storage.save_or_create(
                key_or_filename,
                sorted_urls,
                adapt_list=True
            )

            await run_additional_storages(key_or_filename, sorted_urls)

        async def main():
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

            is_home_page = [
                url.url_object.path == '/',
                self.start_url.url_object.path == '/',
                # To prevent returning an empty list when running
                # the spider for the first time, require at least
                # on rotation before running this check
                self.performance_audit.iteration_count > 0
            ]

            if all(is_home_page):
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
        """Calculate the overall spider performance"""
        async def calculate_urls_performance():
            total_count = sum(
                [
                    len(self.visited_urls),
                    len(self.urls_to_visit)
                ]
            )
            result = len(self.visited_urls) / total_count
            percentage = round(result * 100, 3)
            logger.info(f'{percentage}% of total urls visited')

        async def main():
            await asyncio.create_task(calculate_urls_performance())

            data = self.performance_audit.json()
            await self.storage.save_or_create('performance.json', data)

        asyncio.run(main())

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
        """Use this function to load a storage on the class
        using a pyton path e.g. storages.FileStorage. The storage
        should be a subclass of `BaseStorage`"""
        try:
            klass = import_from_module(python_path)
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

    def non_default_storage_by_name(self, name):
        candidates = list(filter(lambda x: x[0] == name, self.additional_storages))
        if len(candidates) == 0:
            return False
        return candidates[-1]

    def setup_class(self):
        """A function that sets up the final elements of the
        class before actually running the spider e.g. storages"""
        default_storage_path = settings.STORAGES.get('default')
        klass = self.load_storage(default_storage_path)

        params = {'spider': self}
        if getattr(klass, 'file_based'):
            params['storage_path'] = settings.MEDIA_FOLDER

        self.storage = klass(**params)

        if self.storage.is_connected:
            logger.info(f"Default storage: {color_text('blue', default_storage_path)}")
        
        # Even though the user swapped out the file based storage
        # for a cloud one, we will still need the file based one
        # for simple local operations. So reimplement it.
        is_swapped = default_storage_path != 'kryptone.data_storages.FileStorage'
        if is_swapped:
            settings.STORAGES['backends'].append(
                {
                    'name': 'basic',
                    'storage': 'kryptone.data_storages.FileStorage'
                }
            )

        other_storages_path = settings.STORAGES.get('backends', [])
        for storage_info in other_storages_path:
            other = self.load_storage(storage_info['storage'])

            params = {'spider': self}
            if getattr(other, 'file_based'):
                params['storage_path'] = settings.MEDIA_FOLDER
            
            instance = other(**params)
            custom_name = storage_info['name']
            self.additional_storages.append((custom_name, instance))

        if other_storages_path:
            logger.info(f"Attached additional storages: {other_storages_path}")

        # Here we are going to check the file that allows
        # us to keep track of the uuid constant which will
        # allow other backends to be able to consistently
        # track the state for the given spider -; storages
        # like Redis rely on this conssitent uuuid ortherwise
        # a new key will always be created preventing us from
        # updating the data consistently
        if is_swapped:
            _, storage = self.non_default_storage_by_name('basic')
        else:
            storage = self.storage

        file_exists = async_to_sync(storage.has)('uuid_map.json')
        if file_exists:
            file = async_to_sync(storage.get_file)('uuid_map.json')
            existing_data = async_to_sync(file.read)()

            # Re-use an existing uuid so that other backends can
            # track the state of the spider
            exisiting_uuid = existing_data.get(self.__class__.__name__)
            if exisiting_uuid is not None:
                self.spider_uuid = exisiting_uuid
            logger.warning(f'Re-using known uuid: {color_text('yellow', self.spider_uuid)}')
        else:            
            data = {f'{self.__class__.__name__}': str(self.spider_uuid)}
            async_to_sync(storage.save_or_create)('uuid_map.json', data)
            file = async_to_sync(storage.get)('uuid_map.json')
            logger.warning(f'Created uuid file @ {color_text('blue', file.path)}')

    def before_start(self, start_urls, *args, **kwargs):
        # TODO: Maybe reunite the "before_start" and the
        # "setup_class" funcitons into one single function
        # "setup_class"
        if self._meta.debug_mode:
            logger.debug(color_text('blue', 'Starting Kryptone in debug mode', background=True))
        else:
            logger.info(color_text('green', 'Starting Kryptone', background=True))

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

        logger.info(f'{color_text('blue', self.__class__.__name__)} ready to crawl website')

        if self.start_url is None:
            self.start_url = URL(start_urls[-1])
        self.add_urls(start_urls)

    def start(self, start_urls=[], **kwargs):
        skip_setup = kwargs.get('skip_setup', False)
        if not skip_setup:
            self.setup_class()

        self.before_start(start_urls, **kwargs)
        logger.info(f'Spider ID is: {color_text('green', str(self.spider_uuid))}')

        if self._meta.debug_mode:
            # TODO: Create a simplified version of the start funciton in
            # order to test the other functions of this class
            logger.warning("Calling start in debug mode will have no effect")
            return False

        maximize_window = kwargs.get('maximize_window', True)
        if maximize_window:
            self.driver.maximize_window()

        wait_time = settings.WAIT_TIME
        next_execution_date = None

        while self.urls_to_visit:
            if next_execution_date is not None:
                if self.get_current_date < next_execution_date:
                    continue

            current_url = URL(self.urls_to_visit.pop())
            logger.info(f"{color_text('green', len(self.urls_to_visit))} urls left to visit")

            if current_url.is_empty:
                continue

            if not current_url.is_same_domain(self.start_url):
                continue

            # TODO: Factorize this section into one single function
            # from 859:935 so that it can be used by both start and
            # bootstart without having to write two codes

            logger.info(f'Going to url: {color_text('green', current_url)}')

            try:
                self.driver.get(str(current_url))
            except Exception as e:
                logger.critical(f'Failed to go to: {color_text('red', current_url)}: {e.args}')
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
                self.calculate_performance()

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

            self.performance_audit.count_urls_to_visit = len(
                self.urls_to_visit
            )
            self.performance_audit.count_visited_urls = len(self.visited_urls)

            logger.info(f"Next execution time: {color_text('blue', next_execution_date)}")

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

    def resume(self, windows=1, **kwargs):
        """Resume a previous crawling sessiong by reloading
        data from the urls to visit and visited urls json files
        if present. The presence of previous data is checked 
        in order by doing the following :

        - Redis is checked as the primary database for a cache
        - Memcache is checked in second place
        - Finally, the file cache is used as a final resort if none exists
        """
        self.setup_class()
        # The spider will use the default storage
        # in order to resume its previous state. This
        # can be altered by providing a "source" that
        # indicates the index of the alternative storage
        # to use -- note: using an alternative storage will
        # overwrite all the data stored in the other
        # storage pool
        # source = kwargs.get('soure', None)
        # if source is not None:
        #     try:
        #         storage = self.additional_storages[source]
        #     except IndexError:
        #         raise Exception(
        #             "The storage you are trying to get does not "
        #             "exist in your STORAGES.backends"
        #         )
        #     else:
        #         # TODO: In order to use none file based storages,
        #         # we need to know the previous spider uuid, not
        #         # the current one created above
        #         if not storage.file_based:
        #             urls_to_visit = storage.get('urls_to_vist')
        #             visited_urls = storage.get('visited_urls')
        # else:
        data = self.storage.get('cache.json')

        self.start_url = URL(self._meta.start_urls[0])

        urls_to_visit = self.check_urls(data['urls_to_visit'])
        visited_urls = self.check_urls(data['visited_urls'])

        self.urls_to_visit = urls_to_visit
        self.visited_urls = visited_urls

        state = self.storage.has('seen_urls.csv')
        if not state:
            logger.warning(
                "Could not find the file for urls that were "
                "previously seen on the website. The spider could "
                "revisit urls that were already visited"
            )

        if self.storage.has('performance.json'):
            data = self.storage.get('performance.json')
            self.performance_audit.load_statistics(data)

        if windows > 1:
            self.boost_start(windows=windows, **kwargs)
        else:
            self.start(skip_setup=True, **kwargs)

    def start_from_sitemap_xml(self, url, windows=1, **kwargs):
        return NotImplemented

    def start_from_json(self, windows=1, **kwargs):
        return NotImplemented

    def boost_start(self, start_urls=[], *, windows=1, **kwargs):
        """Calling this method will make selenium open either
        multiple windows or multiple tabs for the project.$
        Selenium will open an url in each window or tab and
        sequentically call `current_page_actions` on the
        given page"""
        self.setup_class()
        self.before_start(start_urls, **kwargs)

        wait_time = settings.WAIT_TIME

        # Create the amount of tabs/windows
        # necessary for visiting each page
        for i in range(windows):
            self.driver.switch_to.new_window('tab')

        # Get position on the first opened window
        # as opposed to the being on the last created one
        self.driver.switch_to.window(self.driver.window_handles[0])
        next_execution_date = None

        while self.urls_to_visit:
            if next_execution_date is not None:
                if self.get_current_date < next_execution_date:
                    continue

            current_urls = []

            # 1. Create a batch of urls to visit
            # and navigate to
            for _ in self.driver.window_handles:
                try:
                    # In the very start we could have just
                    # one url available to visit. In which
                    # case, just pass. We'll go to the pages
                    # when we get more urls to use in the tabs
                    current_url = URL(self.urls_to_visit.pop())
                except:
                    continue
                else:
                    if current_url.is_empty:
                        continue
                    current_urls.append(str(current_url))

            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            # 2. Load each urls into the tabs
            url_instances = []

            for i, handle in enumerate(self.driver.window_handles):
                try:
                    # Same. If we only had one url
                    # to start with, this will raise
                    # IndexError - so just skip
                    current_url = URL(current_urls[i])
                except IndexError:
                    continue

                self.driver.switch_to.window(handle)

                # If we are not on the same domain as the
                # starting url: *stop*. we are not interested
                # in exploring the whole internet
                if not current_url.is_same_domain(self.start_url):
                    continue

                logger.info(f'Going to url: {current_url}')

                if self._meta.ignore_images:
                    if current_url.is_image:
                        continue

                self.driver.get(str(current_url))
                self.visited_pages_count = self.visited_pages_count + 1

                try:
                    # Always wait for the body section of
                    # the page to be located  or visible
                    wait = WebDriverWait(self.driver, 5)
                    wait.until(
                        EC.presence_of_element_located(
                            (
                                By.TAG_NAME,
                                'body'
                            )
                        )
                    )
                except:
                    logger.error('Body element of page was not detected')

                self.post_navigation_actions(current_url)

                self.visited_urls.add(current_url)
                url_instances.append(current_url)

            # 3. Run the custom actions on the page
            for i, handle in enumerate(self.driver.window_handles):
                try:
                    url_instance = url_instances[i]
                except IndexError:
                    continue

                self.driver.switch_to.window(handle)

                if self._meta.crawl:
                    self.collect_page_urls()
                else:
                    self.visited_urls.add(current_url)
                    self.list_of_seen_urls.add(current_url)

                self.backup_urls()

                try:
                    # Run custom user actions once
                    # everything is completed
                    self.current_page_actions(url_instance)
                except TypeError as e:
                    logger.info(e)
                    raise TypeError(
                        "'self.current_page_actions' "
                        f"should be able to accept arguments: {e}"
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
                        self.collect_page_urls()
                        self.backup_urls()

                # Run routing actions aka, base on given
                # url path, route to a function that
                # would execute said task
                if self._meta.router is not None:
                    self._meta.router.resolve(url_instance, self)

                if self._meta.crawl:
                    self.calculate_performance()

                self.performance_audit.add_iteration_count()

            if settings.WAIT_TIME_RANGE:
                start = settings.WAIT_TIME_RANGE[0]
                stop = settings.WAIT_TIME_RANGE[1]
                wait_time = random.randrange(start, stop)

            next_execution_date = (
                self.get_current_date +
                datetime.timedelta(seconds=wait_time)
            )

            if len(self.urls_to_visit) == 0:
                self.performance_audit.end_date = self.get_current_date
                self.performance_audit.calculate_duration()

            self.performance_audit.count_urls_to_visit = len(
                self.urls_to_visit
            )
            self.performance_audit.count_visited_urls = len(self.visited_urls)

            if os.getenv('KYRPTONE_TEST_RUN') is not None:
                break

            logger.info(f"Next execution time: {next_execution_date}")

            current_urls.clear()
            url_instances.clear()
