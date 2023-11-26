import asyncio
import time
from collections import OrderedDict, defaultdict
from urllib.parse import unquote, urlparse

from kryptone import logger
from kryptone.utils.urls import URL


class MockupSpider:
    """Mockup spider used for testing
    the logic behing the main spider"""

    start_url = None
    urls_to_visit = set()
    visited_urls = set()
    list_of_seen_urls = set()

    class Meta:
        url_gather_ignore_tests = []

    def url_structural_check(self, url):
        """Checks the structure of an
        incoming url"""
        url = str(url)
        clean_url = unquote(url)
        if url.startswith('/'):
            clean_url = self.urljoin(clean_url)
        return clean_url, urlparse(clean_url)

    def url_filters(self, valid_urls):
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
                f"Filters completed. {len(urls_removed)} url(s) removed")
            return urls_kept
        return valid_urls

    def get_page_urls(self, current_url, refresh=False):
        raw_urls = [
            'http://example/2',
            'http://example.com/1',
            'http://example.com/8'
        ]

        if self.META.url_gather_ignore_tests:
            matched_pattern = None
            for regex in self.Meta.url_gather_ignore_tests:
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

            if clean_url in self.urls_to_visit:
                invalid_urls.add(clean_url)
                continue

            if clean_url in self.visited_urls:
                invalid_urls.add(clean_url)
                continue

            valid_urls.add(clean_url)

        self.list_of_seen_urls.update(valid_urls)
        self.list_of_seen_urls.update(invalid_urls)

        newly_discovered_urls = []
        for url in valid_urls:
            if url not in self.list_of_seen_urls:
                newly_discovered_urls.append(url)

        filtered_valid_urls = self.url_filters(valid_urls)
        self.urls_to_visit.update(filtered_valid_urls)

    def run_actions(self, url_instance, **kwargs):
        pass

    def start(self):
        if not self.urls_to_visit:
            self.urls_to_visit.add(self.start_url)
            self.list_of_seen_urls.add(self.start_url)

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.info(f"{len(self.urls_to_visit)} urls left to visit")

            if current_url is None:
                continue

            logger.info(f'Going to url: {current_url}')
            self.visited_urls.add(current_url)

            self.get_page_urls()

            url_instance = URL(current_url)
            self.run_actions(url_instance)

            logger.info(f"Waiting 2s")
            time.sleep(5)


class BaseTestSpider(MockupSpider):
    start_url = 'http://example.com/1'

    def handle_1(self, current_url, route=None):
        pass

    def handle_2(self, current_url, route=None):
        pass


async def main():
    # async def one():
    #     a = await asyncio.sleep(1, result='Great!')
    #     print(a)
    #     print('a')

    # async def two():
    #     print('b')

    # await asyncio.gather(one(), two())

    async def one():
        print('a')
        await asyncio.sleep(3)

    async def two():
        print('b')

    # t1 = asyncio.create_task(one())
    # t2 = asyncio.create_task(two())

    # await t1
    # await t2

    # async with asyncio.TaskGroup() as t:
    #     t1 = asyncio.create_task(one())
    #     t2 = asyncio.create_task(two())

    # t1 = asyncio.create_task(one())
    # t2 = asyncio.create_task(two())
    # # await asyncio.wait([t1, t2])
    # r = asyncio.as_completed([t1, t2])
    # for x in r:
    #     v = await x
    #     print(v)
    return 1


w = asyncio.run(main())
print(w)
