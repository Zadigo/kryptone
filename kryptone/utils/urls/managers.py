import datetime
import itertools
from collections import OrderedDict, defaultdict
from functools import lru_cache
from typing import Any, Callable, Optional, Sequence
from urllib.parse import (
    urljoin,
)
import asyncio
import bisect
import pandas
import pytz

from kryptone import logger
from kryptone.utils.date_functions import get_current_date
from kryptone.internal_types import TypeSiteCrawler, TypeUrl
from kryptone.utils.urls.base import URL
from kryptone.data_storages import FileStorage
from kryptone.conf import settings


class MultipleURLManager:
    """A class that manages a collection of URLs to visit and
    keeps track of visited URLs. It provides methods to add, filter, and
    retrieve URLs, as well as to maintain statistics about the crawling process.

    Args:
        ignore_images (bool): Whether to ignore image URLs when adding new URLs.
        sort_urls (bool): Whether to sort the URLs to visit.

    Attributes:
        _urls_to_visit (set[URL]): A set of URLs that are yet to be visited.
        _visited_urls (set[URL]): A set of URLs that have already been visited.
        _grouped_by_page (defaultdict[URL, set[URL]]): A dictionary that groups URLs by the page they were found on.
        _current_url (Optional[URL]): The current URL being processed.
        list_of_seen_urls (set[URL]): A set of all URLs that have been seen, regardless of whether they are to be visited or have been visited.
        custom_url_filters (list[Callable[[URL], bool]]): A list of custom filter functions that can be applied to URLs before adding them to the visit list.
    """

    _urls_to_visit: set[URL] = set()
    _visited_urls: set[URL] = set()
    _grouped_by_page: defaultdict[URL, set[URL]] = defaultdict(set)
    _current_url: Optional[URL] = None
    list_of_seen_urls: set[URL] = set()
    custom_url_filters: list[Callable[[URL], bool]] = []

    def __init__(
        self,
        driver: TypeSiteCrawler,
        ignore_images: bool = True,
        sort_urls: bool = False,
    ):
        self._driver = driver
        self.start_url: Optional[URL] = None
        self.ignore_images = ignore_images
        self.sort_urls = sort_urls
        # This attribute is updated every time
        # "get" is called on the class
        self.current_iteration: int = 0
        # A dataframe used to store the urls to visit and visited urls
        # and can be used to export the data to a csv or json file
        self.dataframe: Optional[pandas.DataFrame] = None
        self.visited_pages

    def __repr__(self):
        name = self.__class__.__name__
        return f"<{name} urls_to_visit={self.urls_to_visit_count} visited_urls={self.visited_urls_count}>"

    def __iter__(self):
        for url in self._urls_to_visit:
            yield url

    def __contains__(self, url: URL):
        return any([str(url) in self._urls_to_visit, str(url) in self._visited_urls])

    def __len__(self):
        return len(self._urls_to_visit)

    def __getitem__(self, index: int):
        url = list(self._urls_to_visit)[index]
        return URL(url)

    @property
    def empty(self):
        return len(self._urls_to_visit) == 0

    @property
    def urls_to_visit(self):
        for url in self._urls_to_visit:
            yield URL(url)

    @property
    def visited_urls(self):
        for url in self._visited_urls:
            yield URL(url)

    @property
    def urls_to_visit_count(self):
        return len(self._urls_to_visit)

    @property
    def visited_urls_count(self):
        return len(self._visited_urls)

    @property
    def total_urls_count(self):
        return sum([self.urls_to_visit_count, self.visited_urls_count])

    @property
    def completion_rate(self):
        try:
            result = self.urls_to_visit_count / self.visited_urls_count
            return round(result, 2)
        except ZeroDivisionError:
            return float(0)

    @property
    def next_url(self):
        try:
            return list(self.urls_to_visit)[0]
        except IndexError:
            return None

    @property
    def grouped_by_page(self):
        container: OrderedDict[URL, list[URL]] = OrderedDict()
        for key, values in self._grouped_by_page.items():
            container[key] = list(values)
        return container

    @lru_cache(maxsize=100)
    def all_urls(self):
        return list(itertools.chain(self._visited_urls, self._urls_to_visit))

    def urljoin(self, path: str):
        if self.start_url is None:
            raise Exception(
                "You should call populate at least once "
                "in order to join paths to their base domain"
            )
        return URL(urljoin(str(self.start_url), str(path)))

    def add_urls(self, urls: list[str, URL], refresh: bool = False):
        """Manually add urls to the current urls to
        visit list. This is useful for cases where urls are
        nested in other elements than links and that
        cannot actually be retrieved by the spider

        * Runs `self.check_urls` on each url
        * Runs user custom url filters `self.run_url_filters`
        * Updates `self.urls_to_visit`"""
        checked_urls = self.check_urls(urls, refresh=refresh)
        filtered_urls = self.run_url_filters(checked_urls)
        self._urls_to_visit.update(filtered_urls)

        if self.start_url is not None:
            container = self._grouped_by_page[self.start_url]
            container.update(filtered_urls)

        container = self._grouped_by_page[URL(self._driver.driver.current_url)]
        container.update(checked_urls)

        if self.dataframe is None:
            self.dataframe = pandas.DataFrame({"urls": list(self.urls_to_visit)})
            self.dataframe["visited"] = False
            self.dataframe["visited_on"] = None

            if self.sort_urls:
                self.dataframe = self.dataframe.sort_values("urls")

            result = self.dataframe.urls.to_list()
            self._urls_to_visit.update(result)
        else:
            newdf = pandas.DataFrame({"urls": list(filtered_urls)})
            newdf["visited"] = False
            newdf["visited_on"] = None
            self.dataframe = pandas.concat([self.dataframe, newdf], ignore_index=True)

    def run_url_filters(self, valid_urls: set[URL]):
        """Excludes urls in the list of collected
        urls based on the value of the functions in
        `url_filters`. All conditions should be true
        in order for the url be considered valid to
        be visited"""
        if self.custom_url_filters:
            results = defaultdict(list)
            for url in valid_urls:
                truth_array = results[url]
                for instance in self.custom_url_filters:
                    truth_array.append(instance(url))

            urls_kept = set()
            urls_removed = set()
            final_urls_filtering_audit = OrderedDict()

            for url, truth_array in results.items():
                final_urls_filtering_audit[url] = any(truth_array)

                # Expect all the test results to
                # be false. If only one test turns
                # out being true, then the url is
                # considered to be not valid
                if any(truth_array):
                    urls_removed.add(url)
                    continue
                urls_kept.add(url)

            logger.info(f"Filters completed. {len(urls_removed)} url(s) removed")
            return urls_kept
        return valid_urls

    def check_urls(self, urls: Sequence[TypeUrl], refresh=False):
        raw_urls = set(urls)

        if self.current_iteration > 0:
            logger.info(f"Found {len(raw_urls)} url(s) in total on this page")

        raw_urls_objs = list(map(lambda x: URL(x), raw_urls))

        valid_urls: set[URL] = set()
        invalid_urls: set[URL] = set()

        for url in raw_urls_objs:
            if url.is_path:
                url = self.urljoin(str(url))

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
                url.url_object.path == "/",
                self.start_url.url_object.path == "/",
                # To prevent returning an empty list when running
                # the spider for the first time, require at least
                # on rotation before running this check
                self.current_iteration > 0,
            ]

            if all(is_home_page):
                invalid_urls.add(url)
                continue

            if self.ignore_images:
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
            logger.info(f"Kept {len(valid_urls)} url(s) as valid to visit")

        newly_discovered_urls = []
        for url in valid_urls:
            if url not in self.list_of_seen_urls:
                newly_discovered_urls.append(url)

        if newly_discovered_urls:
            logger.info(f"Discovered {len(newly_discovered_urls)} unseen url(s)")
        return valid_urls

    def backup(self):
        return {
            "date": str(datetime.datetime.now(tz=pytz.UTC)),
            "urls_to_visit": list(self._urls_to_visit),
            "visited_urls": list(self._visited_urls),
            "statistics": {
                "last_visited_url": str(self._current_url)
                if self._current_url is not None
                else None,
                "urls_to_visit_count": self.urls_to_visit_count,
                "visited_urls_count": self.visited_urls_count,
                "total_urls": sum([self.urls_to_visit_count, self.visited_urls_count]),
                "completion_rate": self.completion_rate,
            },
        }

    def clear(self):
        self._urls_to_visit.clear()
        self._visited_urls.clear()

    def reverse(self):
        return list(reversed(self.urls_to_visit))

    def get(self):
        """Destructively returns the next url to visit
        and removes it from the list of urls to visit"""
        if not self._urls_to_visit:
            return None

        url = self._urls_to_visit.pop()
        self._current_url = URL(url)
        self._visited_urls.add(url)

        if self.dataframe is not None:
            found_urls = self.dataframe[self.dataframe.urls == url]
            for item in found_urls.itertuples():
                self.dataframe.loc[item.Index, "visited"] = True
                self.dataframe.loc[item.Index, "visited_on"] = get_current_date()
            self.current_iteration += 1
            return url
        return None

    def populate(self, start_urls: list[str]):
        """Populates the list of urls to visit with a
        list of starting urls. This method should be called at
        least once before starting the crawling process."""
        if self.start_url is None:
            start_url = URL(start_urls[0])
            if start_url.is_path:
                raise ValueError(
                    "The first url in the list of starting urls is a path "
                    "you need to implement a valid url string as a "
                    "first value in the list"
                )
            self.start_url = start_url
            self.add_urls(start_urls)

    def backup_urls(self):
        """Backs up the current state of the URL manager to a storage.
        This method saves the list of URLs to visit and the list of visited URLs
        to a storage, allowing for the crawling session to be resumed later."""
        if self._driver.storage is None:
            self._driver.storage = FileStorage(
                spider=self._driver, storage_path=settings.MEDIA_FOLDER
            )

        async def run_additional_storages(key: str, value: list[Any] | dict[str, Any]):
            for name, storage in self._driver.additional_storages:
                # Only use storages that are connected.
                # This is a none block loop
                if not storage.is_connected:
                    logger.warning(f"Could not use {name}. Connection broken")
                    continue
                await storage.save_or_create(key, value)

        async def write_cache_file():
            data = {
                "spider": self._driver.__class__.__name__,
                "spider_uuid": self._driver.spider_uuid,
                "timestamp": self._driver.get_current_date.strftime(
                    "%Y-%M-%d %H:%M:%S"
                ),
                "urls_to_visit": self._driver.normalize_urls(
                    self._driver.urls_to_visit
                ),
                "visited_urls": self._driver.normalize_urls(self._driver.visited_urls),
            }

            key_or_filename = f"{settings.CACHE_FILE_NAME}.json"

            if self._driver.storage is not None:
                await self._driver.storage.save_or_create(key_or_filename, data)
            await run_additional_storages(key_or_filename, data)

        async def write_seen_urls():
            sorted_urls: list[URL] = []
            for url in self.list_of_seen_urls:
                bisect.insort(sorted_urls, url)

            key_or_filename = "seen_urls.csv"

            if self._driver.storage is not None:
                await self._driver.storage.save_or_create(
                    key_or_filename,
                    self._driver.normalize_urls(sorted_urls),
                    adapt_list=True,
                )

            await run_additional_storages(
                key_or_filename, self._driver.normalize_urls(sorted_urls)
            )

        async def write_url_distribution():
            key_or_filename = "url_distribution.json"

            if self._driver.storage is not None:
                await self._driver.storage.save_or_create(
                    key_or_filename, self.grouped_by_page
                )
            await run_additional_storages(key_or_filename, self.grouped_by_page)

        async def main():
            t1 = asyncio.create_task(write_cache_file())
            t2 = asyncio.create_task(write_seen_urls())
            t3 = asyncio.create_task(write_url_distribution())

            aws = [t1, t2, t3]
            for aw in asyncio.as_completed(aws):
                await aw

        asyncio.run(main())

    def restore(self, urls_to_visit: Sequence[str], visited_urls: Sequence[str]):
        """Restores the state of the URL manager from a backup.
        This method is useful for resuming a crawling session after
        an interruption.

        Args:
            urls_to_visit (Sequence[str]): A sequence of URLs that are yet to be visited.
            visited_urls (Sequence[str]): A sequence of URLs that have already been visited.
        """
        self.add_urls(urls_to_visit)
        self._visited_urls = set(map(lambda x: URL(x), visited_urls))
        self.start_url = self._urls_to_visit.pop() if self._urls_to_visit else None
