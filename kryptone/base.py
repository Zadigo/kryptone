import asyncio
import dataclasses
import datetime
import inspect
import io
import os
import pathlib
import random
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Final, Optional, Sequence
from urllib.parse import unquote, urljoin
from uuid import uuid4

import pytz
import requests
from asgiref.sync import async_to_sync
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from kryptone.process import SeleniumBrowser, SeleniumLauncher
from kryptone import exceptions, logger
from kryptone.conf import settings
from kryptone.data_storages import BaseStorage
from kryptone.internal_types import (
    PerformanceAuditProtocol,
    TypeData,
    TypePath,
    TypeUrl,
)
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.functions import create_filename, directory_from_url
from kryptone.utils.module_loaders import import_from_module
from kryptone.utils.text import color_text
from kryptone.utils.urls.managers import URL, MultipleURLManager
from kryptone.internal_types import TypeStorage

DEFAULT_META_OPTIONS: Final[set[str]] = {
    "domains",
    # List of callables that will be used
    # to filter out urls after they have been
    # collected from the page: URLIgnoreTest, URLIgnoreRegexTest
    # (exclusion test)
    "url_ignore_tests",
    # List of regex patterns used on URL.test_path
    # to validate urls before they are added to the
    # urls to visit list - (exclusion test)
    "url_rule_tests",
    # Whether to run the spider in debug mode
    "debug_mode",
    # Default number of pixels to scroll
    # when scrolling down the page
    "default_scroll_step",
    # Router instance used to manage
    # url routing. Should be an instance of
    # kryptone.routers.BaseRouter which will
    # then route the urls to the appropriate
    # function registered on the spider
    "router",
    # Whether to actually perform crawling
    "crawl",
    # List of urls or url generators used
    # to start the crawling from
    "start_urls",
    # Ignore urls with query strings
    "ignore_queries",
    # Ignore images
    "ignore_images",
    # Restrict url retrieval only to
    # to specific sections of the page
    # e.g. body, div[class="example"]
    "restrict_search_to",
    # List of regex patters used to filter all urls before
    # they are even considered valid to be added to
    # the urls to visit list. The urls will not appear in
    # the seen urls list either - this is useful for not
    # tracking certain types of urls at all (exclusion test)
    "url_gather_ignore_tests",
    "database",
}


class CrawlerOptions:
    """Stores the main options for the crawler"""

    def __init__(self, spider: "SiteCrawler | Crawler", name: str):
        self.spider = spider
        self.spider_name = name.lower()
        self.verbose_name = name.title()
        self.initial_spider_meta = None

        self.domains: list[str] = []
        self.url_ignore_tests: list[Any] = []
        self.debug_mode: bool = False
        self.default_scroll_step: int = 80
        self.router = None
        self.crawl: bool = True
        self.start_urls: list[str] = []
        # Restrict url retrieval only to
        # to specific sections of the page
        # e.g. body, div[class="example"]
        self.restrict_search_to: list[str] = []
        # Ignore urls with query strings
        self.ignore_queries = False
        self.ignore_images = False
        self.url_gather_ignore_tests: list[str] = []
        self.url_rule_tests: list[str] = []

    def __repr__(self):
        return f"<{self.__class__.__name__} for {self.verbose_name}>"

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
        if hasattr(self.start_urls, "resolve_generator"):
            self.start_urls = list(self.start_urls)
        elif isinstance(self.start_urls, list):
            start_urls = []
            for item in self.start_urls:
                if hasattr(item, "resolve_generator"):
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
    timezone = "UTC"
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
        self.duration = self.start_date - self.end_date

    def add_error_count(self):
        self.error_count = self.error_count + 1

    def add_iteration_count(self):
        self.iteration_count = self.iteration_count + 1

    def load_statistics(self, data):
        self.iteration_count = data["iteration_count"]

        date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        self.start_date = datetime.datetime.strptime(data["start_date"], date_format)
        self.start_date.replace(tzinfo=pytz.timezone(data.get("timezone", "UTC")))

        self.count_urls_to_visit = data.get("count_urls_to_visit", 0)
        self.count_visited_urls = data.get("count_visited_urls", 0)

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

        meta_object = attrs.pop("Meta", None)
        meta = CrawlerOptions(new_class, name)
        meta.initial_spider_meta = meta_object
        setattr(new_class, "_meta", meta)

        if meta_object is not None:
            meta_object_dict = meta_object.__dict__

            declared_options = []
            for key, value in meta_object_dict.items():
                if key.startswith("__"):
                    continue

                declared_options.append((key, value))
            meta.add_meta_options(declared_options)

        new_class.prepare()
        return new_class

    def prepare(cls):
        cls._meta.prepare()


class BaseCrawler(metaclass=Crawler):
    DATA_CONTAINER: list = []
    model = None

    list_of_seen_urls: set[URL] = set()
    browser_name: Optional[str] = None
    timezone: str = "UTC"
    default_scroll_step: int = 80

    storage: Optional[TypeStorage] = None
    additional_storages: list[tuple[str, BaseStorage]] = []

    url_manager_class: Final[type[MultipleURLManager]] = MultipleURLManager
    _meta: Final[CrawlerOptions] = None

    def __init__(self, browser_name: Optional[str] = None):
        # A dictionary that allows us to track the
        # distribution of urls per domain or page visited
        # self.url_distribution = defaultdict(list)
        self.spider_uuid = uuid4()

        # The start url which corresponds
        # to the first url of "Meta.start_urls"
        # allows us to track the domain to which
        # crawling needs to be limited to
        # self.start_url: Optional[URL] = None

        self.url_manager: Optional[MultipleURLManager] = self.url_manager_class(self)

        if not self._meta.debug_mode:
            launcher = SeleniumLauncher(
                SeleniumBrowser(
                    browser_name=browser_name or self.browser_name,
                    headless=settings.HEADLESS,
                    load_images=settings.LOAD_IMAGES,
                    load_js=settings.LOAD_JS,
                )
            )
            self.driver = launcher.launch()

    def __repr__(self):
        klass_name = self.__class__.__name__
        return f"<{klass_name}: {self.spider_uuid}>"

    def __hash__(self):
        return hash((self.spider_uuid))

    @property
    def get_page_title(self) -> str:
        element = self.driver.find_element(By.TAG_NAME, "title")
        return element.text

    @property
    def get_current_date(self) -> datetime.datetime:
        timezone = pytz.timezone(self.timezone)
        return datetime.datetime.now(tz=timezone)

    @property
    def get_origin(self):
        if self.url_manager and self.url_manager.start_url:
            return self.url_manager.start_url.domain

        # if self.start_url is None:
        #     return ""

        # return urlunparse(
        #     (
        #         self.start_url.url_object.scheme,
        #         self.start_url.url_object.netloc,
        #         None,
        #         None,
        #         None,
        #         None,
        #     )
        # )

    # @cached_property
    # def calculate_completion_percentage(self) -> float:
    #     return len(self.visited_urls) / len(self.urls_to_visit)

    @staticmethod
    def normalize_urls(urls: Sequence[URL]) -> list[str]:
        """Converts a list of URL objects to strings"""
        return [str(url) for url in urls]

    def download_images(
        self,
        urls: Sequence[str],
        page_url: TypeUrl,
        directory: Optional[TypePath] = None,
        exclude_paths: list[str] = [],
        filename_attrs={},
    ):
        """A method that can be called with a list of image urls to download. The
        images will be stored the indicated media folder"""
        if not isinstance(urls, list):
            return False

        try:
            from PIL import Image
        except ImportError:
            return False

        async def save_image(url: URL, img: Any):
            qualified_directory = None
            if directory is None:
                # Use the default url structure to determine
                # the actual directory structure for the image
                qualified_directory = directory_from_url(
                    page_url, exclude=exclude_paths
                )
            else:
                if isinstance(directory, str):
                    qualified_directory = pathlib.Path(directory)
                else:
                    qualified_directory = directory

            qualified_directory: pathlib.Path = settings.MEDIA_FOLDER.joinpath(
                qualified_directory
            )
            if not qualified_directory.exists():
                qualified_directory.mkdir()

            inferred_filename = url.get_filename
            if inferred_filename is None:
                logger.warning(
                    color_text(
                        "yellow",
                        "File name could not be infered "
                        "from url. Using random characters",
                    )
                )
                filename_attrs.update(suffix_with_date=True)
                inferred_filename = create_filename(**filename_attrs)
            else:
                name, extension = inferred_filename.split(".")
                if "suffix" not in filename_attrs:
                    filename_attrs.update(suffix=name)
                filename_attrs.update(extension=extension)
                inferred_filename = create_filename(**filename_attrs)

            filepath = qualified_directory.joinpath(inferred_filename)

            pil_extension = "JPEG"
            if url.get_extension == ".png":
                pil_extension = "PNG"

            try:
                img.save(filepath, format=pil_extension)
            except Exception as e:
                logger.error(e)
            else:
                logger.info(f"Downloaded image: {url}")

        async def image_reader(url: URL, buffer: io.BytesIO):
            img = Image.open(buffer)

            refactored_img = None
            # image_data = img.getdata()
            resize = getattr(settings, "IMAGE_DOWNLOAD_RESIZE", ())
            if resize:
                if len(resize) < 1:
                    raise ValueError("Resize should be a tuple of two values")

                resize = list(resize)
                dimensions = (img.width // resize[0], img.height // resize[1])
                refactored_img = img.resize(dimensions)

            if refactored_img is None:
                refactored_img = img

            await save_image(url, refactored_img)
            return refactored_img

        async def downloader(task_group: asyncio.TaskGroup, url: str):
            try:
                response = requests.get(url)
            except Exception:
                logger.warning(f"Could not download image: {color_text('red', url)}")
                return False
            else:
                if response.status_code == 200:
                    buffer = io.BytesIO(response.content)
                    await task_group.create_task(image_reader(URL(url), buffer))

        async def main():
            tasks: list[asyncio.Task] = []

            async with asyncio.TaskGroup() as tg:
                for url in urls:
                    task = tg.create_task(downloader(tg, url))
                    task.add_done_callback(lambda t: tasks.append(t))

                await asyncio.gather(*tasks)

        asyncio.run(main())

        if self.storage is not None:
            self.storage.initialize()

    def collect_page_urls(self):
        """Returns all the links present on the
        currently visited page"""
        found_urls: list[str] = []
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
                        f"Found {len(urls)} url(s) in page section: '{selector}'"
                    )
                found_urls.extend(urls)
        else:
            found_urls = self.driver.execute_script(
                """
                const urls = Array.from(document.querySelectorAll('a'))
                return urls.map(x => x.href)
                """
            )

        # self.url_distribution[self.driver.current_url].extend(found_urls)
        return found_urls

    def save_object(self, data: TypeData, check_fields_null: list[str] = []):
        """Saves a new object in the container"""
        if self.model is None:
            raise ValueError(
                "You need to implement a dataclass model "
                "on the spider when trying to use save"
            )

        if not dataclasses.is_dataclass(self.model):
            raise ValueError("Your model should be an instance of of a dataclass")

        if isinstance(data, dict):
            data = [data]

        instance_fields = dataclasses.fields(self.model)
        # TODO: Try catch to raise error detail when user
        # is trying to save with non-model keys
        instances = map(lambda x: self.model(**x), data)

        for instance in instances:
            for field in instance_fields:
                func_name = f"clean_{field.name}"
                if hasattr(instance, func_name):
                    result = getattr(instance, func_name)(getattr(instance, field.name))
                    setattr(instance, field.name, result)

            for check_field in check_fields_null:
                if getattr(instance, check_field) is None:
                    continue

            logger.info(f"Saving: {instance}")
            self.DATA_CONTAINER.append(instance)

    def urljoin(self, path: TypeUrl):
        """Returns the domain of the current
        website"""
        path = str(path).strip()
        result = urljoin(str(self.get_origin), path)
        return URL(unquote(result))

    def calculate_performance(self):
        """Calculate and/log the overall spider performance"""
        if self.url_manager is None:
            raise ValueError(
                "Url manager is not initialized. "
                "Make sure to call 'setup_class' before starting the spider"
            )

        async def log_urls_performance():
            logger.info(f"{self.url_manager.completion_rate}% of total urls visited")

        async def main():
            data = self.performance_audit.json()

            await asyncio.create_task(log_urls_performance())
            if self.storage is not None:
                await self.storage.save_or_create("performance.json", data)

        asyncio.run(main())

    def current_page_actions(self, current_url: URL, **kwargs):
        """Custom actions to execute on the current page.

        >>> class MyCrawler(SiteCrawler):
        ...     def current_page_actions(self, current_url, **kwargs):
        ...         text = self.driver.find_element('h1').text
        """
        return NotImplemented

    def post_navigation_actions(self, current_url: URL, **kwargs: Any):
        """Actions to run on the page immediately after
        the crawler has visited a page e.g. clicking
        on cookie button banner"""
        return NotImplemented

    def before_next_page_actions(self, current_url: URL, next_url: URL, **kwargs: Any):
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

    def after_data_save(self, data: TypeData):
        return NotImplemented

    def before_start(self, start_urls: list[TypeUrl], *args, **kwargs):
        return NotImplemented


class OnPageActionsMixin:
    def click_consent_button(
        self,
        element_id: Optional[str] = None,
        element_class: Optional[str] = None,
        before_click_wait_time: int = 2,
        wait_time: Optional[int] = None,
    ):
        """Click the consent to cookies button which often
        tends to appear on websites"""
        try:
            element = None
            if element_id is not None:
                element = self.driver.find_element(By.ID, element_id)

            if element_class is not None:
                element = self.driver.find_element(By.CLASS_NAME, element_class)

            if element is not None and before_click_wait_time:
                time.sleep(before_click_wait_time)

            element.click()
        except Exception:
            logger.info("Consent button not found")
        finally:
            # Some websites might create an issue when
            # trying to gather the urls of page just
            # after clicking the consent button. Using
            # the wait time can prevent the stale element
            # error from being raised
            if wait_time is not None:
                time.sleep(wait_time)


class SiteCrawler(OnPageActionsMixin, BaseCrawler):
    def __init__(self, browser_name: Optional[str] = None):
        super().__init__(browser_name=browser_name)

        self.start_date = get_current_date(timezone=self.timezone)
        self.end_date: Optional[datetime.datetime] = None
        self.performance_audit: PerformanceAuditProtocol = Performance()
        self.performance_audit.timezone = self.timezone

    def __del__(self):
        try:
            self.driver.quit()
        except Exception:
            pass
        logger.info("Project stopped")

    @staticmethod
    def transform_string_urls(urls: Sequence[TypeUrl]):
        for url in urls:
            yield URL(url) if isinstance(url, str) else url

    def load_storage(self, python_path: str):
        """Use this function to load a storage on the class
        using a pyton path e.g. storages.FileStorage. The storage
        should be a subclass of `BaseStorage`"""
        try:
            klass = import_from_module(python_path)
        except Exception:
            raise ValueError(f"Could not load storage module: {python_path}")

        if not issubclass(klass, BaseStorage):
            raise ValueError(f"{klass} should be an instance of BaseStorage")

        return klass

    def non_default_storage_by_name(self, name: str):
        candidates = list(filter(lambda x: x[0] == name, self.additional_storages))

        if len(candidates) == 0:
            return False, False

        return candidates[-1]

    def setup_class(self):
        """A function that sets up the final elements of the
        class before actually running the spider e.g. storages"""
        default_storage_path = settings.STORAGES.get("default")
        klass = self.load_storage(default_storage_path)

        params = {"spider": self}
        if getattr(klass, "file_based"):
            params["storage_path"] = settings.MEDIA_FOLDER

        self.storage = klass(**params)

        if self.storage.is_connected:
            logger.info(f"Default storage: {color_text('blue', default_storage_path)}")

        # Even though the user swapped out the file based storage
        # for a cloud one, we will still need the file based one
        # for simple local operations. So reimplement it.
        is_swapped = default_storage_path != "kryptone.data_storages.FileStorage"
        if is_swapped:
            settings.STORAGES["backends"].append(
                {"name": "basic", "storage": "kryptone.data_storages.FileStorage"}
            )

        other_storages_path = settings.STORAGES.get("backends", [])
        for storage_info in other_storages_path:
            other = self.load_storage(storage_info["storage"])

            params = {"spider": self}
            if getattr(other, "file_based"):
                params["storage_path"] = settings.MEDIA_FOLDER

            instance = other(**params)
            custom_name = storage_info["name"]
            self.additional_storages.append((custom_name, instance))

        if other_storages_path:
            logger.info(f"Attached additional storages: {storage_info['storage']}")

        # Here we are going to check the file that allows
        # us to keep track of the uuid constant which will
        # allow other backends to be able to consistently
        # track the state for the given spider -; storages
        # like Redis rely on this conssitent uuuid ortherwise
        # a new key will always be created preventing us from
        # updating the data consistently
        if is_swapped:
            # FIXME: This could maybe lead to issues because storage
            # here is a string path and not an actual storage instance
            _, storage = self.non_default_storage_by_name("basic")
        else:
            storage = self.storage

        if storage:
            file_exists = async_to_sync(storage.has)("uuid_map.json")
            if file_exists:
                file = async_to_sync(storage.get_file)("uuid_map.json")
                existing_data = async_to_sync(file.read)()

                # Re-use an existing uuid so that other backends can
                # track the state of the spider
                exisiting_uuid = existing_data.get(self.__class__.__name__)
                if exisiting_uuid is not None:
                    self.spider_uuid = exisiting_uuid
                logger.warning(
                    f"Re-using known uuid: {color_text('yellow', self.spider_uuid)}"
                )
            else:
                data = {f"{self.__class__.__name__}": str(self.spider_uuid)}
                async_to_sync(storage.save_or_create)("uuid_map.json", data)
                file = async_to_sync(storage.get_file)("uuid_map.json")
                logger.warning(f"Created uuid file @ {color_text('blue', file.path)}")

    def before_start(self, start_urls: Sequence[TypeUrl], *args, **kwargs):
        if self.url_manager is None:
            raise ValueError(
                "Url manager is not initialized. "
                "Make sure to call 'setup_class' before starting the spider"
            )

        # TODO: Maybe reunite the "before_start" and the
        # "setup_class" funcitons into one single function
        # "setup_class"
        if self._meta.debug_mode:
            logger.debug(
                color_text("blue", "Starting Kryptone in debug mode", background=True)
            )
        else:
            logger.info(color_text("green", "Starting Kryptone", background=True))

        # It's either the spider is used inline and the urls
        # are provided directly to the start function
        # or the urls are provided in the Meta class
        start_urls = start_urls or self._meta.start_urls

        is_generator = any(
            [hasattr(start_urls, "resolve_generator"), inspect.isgenerator(start_urls)]
        )

        if is_generator:
            start_urls = list(start_urls)

        # Merge the provided start urls with the ones present
        # in the Meta class
        if self._meta.has_start_urls:
            self._meta.start_urls.extend(start_urls)

        start_urls = list(self.transform_string_urls(start_urls))

        # If we have absolutely no start_url and at the
        # same time we have no start_urls, raise an error
        if not start_urls:
            raise exceptions.BadImplementationError(
                "No start urls was used. Provide start urls list "
                "in spider.Meta to start crawling a list of urls"
            )

        logger.info(
            f"{color_text('blue', self.__class__.__name__)} ready to crawl website"
        )

        if self.start_url is None:
            self.start_url = URL(start_urls[-1])

        self.url_manager.add_urls(start_urls)

    def start(self, start_urls: Sequence[TypeUrl] = [], **kwargs: str | bool):
        skip_setup = kwargs.get("skip_setup", False)
        if not skip_setup:
            self.setup_class()

        self.before_start(start_urls, **kwargs)
        logger.info(f"Spider ID is: {color_text('green', str(self.spider_uuid))}")

        if self._meta.debug_mode:
            # TODO: Create a simplified version of the start funciton in
            # order to test the other functions of this class
            logger.warning("Calling start in debug mode will have no effect")
            return False

        maximize_window = kwargs.get("maximize_window", True)
        if maximize_window:
            self.driver.maximize_window()

        wait_time = settings.WAIT_TIME
        next_execution_date = None

        while self.urls_to_visit:
            if next_execution_date is not None:
                if self.get_current_date < next_execution_date:
                    continue

            current_url = URL(self.urls_to_visit.pop())
            logger.info(
                f"{color_text('green', len(self.urls_to_visit))} urls left to visit"
            )

            if current_url.is_empty:
                continue

            if not current_url.is_same_domain(self.start_url):
                continue

            # TODO: Factorize this section into one single function
            # from 859:935 so that it can be used by both start and
            # bootstart without having to write two codes

            logger.info(f"Going to url: {color_text('green', current_url)}")

            try:
                self.driver.get(str(current_url))
            except Exception as e:
                logger.critical(
                    f"Failed to go to: {color_text('red', current_url)}: {e.args}"
                )
                continue

            try:
                # Always wait for the body section of
                # the page to be located  or visible
                wait = WebDriverWait(self.driver, 5)

                condition = EC.presence_of_element_located((By.TAG_NAME, "body"))
                wait.until(condition)
            except Exception:
                logger.critical("Body element of page was not located")
                continue
            else:
                if inspect.iscoroutinefunction(self.post_navigation_actions):
                    async_to_sync(self.post_navigation_actions)(current_url)
                else:
                    self.post_navigation_actions(current_url)

            self.url_manager._visited_urls.add(current_url)

            if self._meta.crawl:
                self.url_manager.add_urls(self.collect_page_urls())
                self.url_manager.backup_urls()

            current_page_actions_params = {}

            try:
                if inspect.iscoroutinefunction(self.current_page_actions):
                    async_to_sync(self.current_page_actions)(
                        current_url, **current_page_actions_params
                    )
                else:
                    self.current_page_actions(
                        current_url, **current_page_actions_params
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
                    "to execute 'current_page_actions'",
                    [Exception(e), exceptions.SpiderExecutionError()],
                )
            else:
                # Refresh the urls once the
                # user actions have been completed
                # for example scrolling down a page
                # that could generate new urls to
                # disover or changing a filter
                if self._meta.crawl:
                    self.url_manager.add_urls(
                        self.collect_page_urls(),
                        refresh=True,
                    )
                    self.url_manager.backup_urls()

            try:
                next_url = self.urls_to_visit[-1]
            except Exception:
                pass
            else:
                if inspect.iscoroutinefunction(self.before_next_page_actions):
                    async_to_sync(self.before_next_page_actions)(current_url, next_url)
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

            next_execution_date = self.get_current_date + datetime.timedelta(
                seconds=wait_time
            )

            self.performance_audit.add_iteration_count()

            if len(self.urls_to_visit) == 0:
                self.performance_audit.end_date = self.get_current_date
                self.performance_audit.calculate_duration()

            self.performance_audit.count_urls_to_visit = len(self.urls_to_visit)
            self.performance_audit.count_visited_urls = len(self.visited_urls)

            logger.info(
                f"Next execution time: {color_text('blue', next_execution_date)}"
            )

            if os.getenv("KYRPTONE_TEST_RUN") is not None:
                break

    def resume(self, windows: int = 1, **kwargs: str | bool):
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
        data = async_to_sync(self.storage.get)("cache.json")

        self.start_url = URL(self._meta.start_urls[0])

        urls_to_visit = self.check_urls(data["urls_to_visit"])
        visited_urls = self.check_urls(data["visited_urls"])

        self.urls_to_visit = urls_to_visit
        self.visited_urls = visited_urls

        state = async_to_sync(self.storage.has)("seen_urls.csv")
        if not state:
            logger.warning(
                "Could not find the file for urls that were "
                "previously seen on the website. The spider could "
                "revisit urls that were already visited"
            )

        if async_to_sync(self.storage.has)("performance.json"):
            data = async_to_sync(self.storage.get)("performance.json")
            self.performance_audit.load_statistics(data)

        if windows > 1:
            self.boost_start(windows=windows, skip_setup=True, **kwargs)
        else:
            self.start(skip_setup=True, **kwargs)

    def start_from_sitemap_xml(
        self, url: TypeUrl, windows: Optional[int] = 1, **kwargs: str | bool
    ):
        return NotImplemented

    def start_from_json(self, windows: Optional[int] = 1, **kwargs: str | bool):
        return NotImplemented

    def boost_start(
        self,
        start_urls: Sequence[TypeUrl] = [],
        *,
        windows: int = 1,
        **kwargs: str | bool,
    ):
        """Calling this method will make selenium open either
        multiple windows or multiple tabs for the project.$
        Selenium will open an url in each window or tab and
        sequentically call `current_page_actions` on the
        given page"""

        skip_setup = kwargs.get("skip_setup", False)
        if not skip_setup:
            self.setup_class()

        self.before_start(start_urls, **kwargs)

        wait_time = settings.WAIT_TIME

        # Create the amount of tabs/windows
        # necessary for visiting each page
        for i in range(windows):
            self.driver.switch_to.new_window("tab")

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
                except Exception:
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

                logger.info(f"Going to url: {current_url}")

                if self._meta.ignore_images:
                    if current_url.is_image:
                        continue

                self.driver.get(str(current_url))
                self.visited_pages_count = self.visited_pages_count + 1

                try:
                    # Always wait for the body section of
                    # the page to be located  or visible
                    wait = WebDriverWait(self.driver, 5)
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                except Exception:
                    logger.error("Body element of page was not detected")

                if inspect.iscoroutinefunction(self.post_navigation_actions):
                    async_to_sync(self.post_navigation_actions)(current_url)
                else:
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
                    if inspect.iscoroutinefunction(self.current_page_actions):
                        async_to_sync(self.current_page_actions)(url_instance)
                    else:
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
                        [Exception(e), exceptions.SpiderExecutionError()],
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

            next_execution_date = self.get_current_date + datetime.timedelta(
                seconds=wait_time
            )

            if len(self.urls_to_visit) == 0:
                self.performance_audit.end_date = self.get_current_date
                self.performance_audit.calculate_duration()

            self.performance_audit.count_urls_to_visit = len(self.urls_to_visit)
            self.performance_audit.count_visited_urls = len(self.visited_urls)

            if os.getenv("KYRPTONE_TEST_RUN") is not None:
                break

            logger.info(f"Next execution time: {next_execution_date}")

            current_urls.clear()
            url_instances.clear()
