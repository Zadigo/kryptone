from string import Template
from collections import defaultdict
import bisect
import datetime
import pathlib
import random
import re
from functools import lru_cache
from collections import OrderedDict
from urllib.parse import urljoin, urlparse

import pytz
import requests

from kryptone import logger
from kryptone.conf import settings
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_while
from kryptone.utils.randomizers import RANDOM_USER_AGENT


class URL:
    """Represents an url

    >>> instance URL('http://example.com')
    """

    def __init__(self, url_string):
        self.raw_url = url_string
        self.url_object = urlparse(self.raw_url)

    def __repr__(self):
        return f'<URL: {self.raw_url}>'

    def __str__(self):
        return self.raw_url

    def __eq__(self, obj):
        return self.raw_url == obj

    def __add__(self, obj):
        return urljoin(self.raw_url, obj)

    def __contains__(self, obj):
        return obj in self.raw_url

    def __hash__(self):
        return hash((self.raw_url, self.url_object.path))

    def __len__(self):
        return len(self.raw_url)

    @property
    def is_path(self):
        return self.raw_url.startswith('/')

    @property
    def is_valid(self):
        return any([
            self.raw_url.startswith('http://'),
            self.raw_url.startswith('https://')
        ])

    @property
    def has_fragment(self):
        return any([
            self.url_object.fragment != '',
            self.raw_url.endswith('#')
        ])

    @classmethod
    def create(cls, url):
        return cls(url)

    @property
    def is_file(self):
        path = settings.GLOBAL_KRYPTONE_PATH / 'data/file_extensions.txt'
        file_extensions = read_document(path, as_list=True)
        extension = self.as_path.suffix

        if extension == '':
            return False

        if self.as_path.suffix in file_extensions:
            return True
        return False

    @property
    def as_path(self):
        return pathlib.Path(self.raw_url)

    @property
    def get_extension(self):
        if self.is_file:
            return self.as_path.suffix
        return None

    @property
    def url_stem(self):
        return self.as_path.stem

    def is_same_domain(self, url):
        incoming_url_object = urlparse(url)
        return incoming_url_object.netloc == self.url_object.netloc

    def get_status(self):
        headers = {'User-Agent': RANDOM_USER_AGENT()}
        response = requests.get(self.raw_url, headers=headers)
        return response.ok, response.status_code

    def compare(self, url_to_compare):
        """Checks that the given url has the same path
        as the url to compare

        >>> instance = URL('http://example.com/a')
        ... instance.compare('http://example.com/a')
        """
        if isinstance(url_to_compare, str):
            url_to_compare = self.create(url_to_compare)

        logic = [
            self.url_object.path == url_to_compare.url_object.path,
            url_to_compare.url_object.path == '/' and self.url_object.path == '',
            self.url_object.path == '/' and url_to_compare.url_object.path == ''
        ]
        return any(logic)

    def capture(self, regex):
        """Captures a value in the given url

        >>> instance = URL('http://example.com/a')
        ... result = instance.capture(r'\/a')
        ... result.group(1)
        ... "/a'
        """
        result = re.search(regex, self.raw_url)
        if result:
            return result
        return False

    def test_url(self, regex):
        """Test if an element in the url passes test. The
        whole url is used to perform the test

        >>> instance = URL('http://example.com/a')
        ... instance.test_url('a')
        ... True
        """
        whole_url_search = re.search(regex, self.raw_url)
        if whole_url_search:
            return True
        return False

    def test_path(self, regex):
        """Test if the url's path passes test. Only the
        path is used to perform the test

        >>> instance = URL('http://example.com/a')
        ... instance.test_path(r'\/a')
        ... True
        """
        path_search = re.search(regex, self.url_object.path)
        if path_search:
            return True
        return False

    def decompose_path(self, exclude=[]):
        """Decomposes an url's path

        >>> instance = URL('http://example.com/a/b')
        ... instance.decompose_path(exclude=[])
        ... ["a", "b"]
        """
        result = self.url_object.path.split('/')

        def clean_values(value):
            if value == '':
                return True
            if exclude and value in exclude:
                return True
            return False
        return list(drop_while(clean_values, result))

    def paginate(self, k=10, regex_path=None, param=None):
        """Increase the pagination number provided
        on a given url"""
        if regex_path is None and param is None:
            # If we have nothing, classically, page
            # is used to paginate in urls
            param = 'page'
        return 1


class CompareUrls:
    """Check the similarity between two different urls

    >>> TestUrl('https://example.com', 'http://example.com/')
    ... True
    """

    def __init__(self, current_url, url_to_test):
        if isinstance(current_url, str):
            current_url = URL(current_url)

        if isinstance(url_to_test, str):
            url_to_test = URL(url_to_test)

        self.current_url = current_url
        self.url_to_test = url_to_test
        self.test_result = self.current_url.compare(url_to_test)

    def __repr__(self):
        return f'<TestUrl: result={self.test_result}>'

    def __bool__(self):
        return self.test_result


class BaseURLTestsMixin:
    blacklist = []

    def __call__(self, url):
        pass

    def convert_url(self, url):
        if isinstance(url, URL):
            return url
        return URL(url)


class URLPassesTest(BaseURLTestsMixin):
    """Checks if an url is able to pass
    a given test

    >>> class Spider(BaseCrawler):
            url_passes_tests = [
                URLPassesTest(
                    'simple_test',
                    paths=[
                        '/example'
                    ]
                )
            ]
    """

    def __init__(self, name, *, paths=[], ignore_files=[], reverse=False):
        self.name = name
        self.paths = set(paths)
        self.failed_paths = []
        self.ignore_files = ignore_files
        self.reverve = reverse

    def __call__(self, url):
        result = []

        url = self.convert_url(url)

        for path in self.paths:
            if path in url.url_object.path:
                self.failed_paths.append(path)
                result.append(True)
            else:
                result.append(False)

            # if url.is_file and self.ignore_files:
            #     if url.get_extension in self.ignore_files:
            #         result.append(False)

        if any(result):
            logger.warning(f"{url} failed test '{self.name}'")
            return False
        return True

    @lru_cache(maxsize=10)
    def default_ignored_files(self):
        path = settings.GLOBAL_KRYPTONE_PATH / 'data/file_extensions.txt'
        sorted_values = sorted(read_document(path, as_list=True))
        return list(drop_while(lambda x: x == '', sorted_values))


class URLPassesRegexTest(BaseURLTestsMixin):
    """Checks if an url is able to pass a
    a given test

    >>> class Spider(BaseCrawler):
            url_passes_tests = [
                URLPassesRegexTest(
                    'simple_test',
                    regex=r'\/a$'
                )
            ]
    """

    def __init__(self, name, *, regex=None, reverse_test=False):
        self.name = name
        self.regex = re.compile(regex)
        # Reverse test means that if the url
        # succeeds the test, it should be kept
        # as opposed to being excluded (defaul
        # behaviour)
        self.reverse_test = reverse_test

    def __call__(self, url):
        result = self.regex.search(url)
        if result:
            return True
        logger.warning(f"{url} failed test: '{self.name}'")
        return False


class URLIterator:
    _urls_to_visit = set()
    _visited_urls = set()
    _seen_urls = set()
    _grouped_by_page = defaultdict(set)
    _current_url = None

    def __init__(self, start_urls=[], sort_urls=False):
        self.sort_urls = sort_urls
        result = self.pre_save(start_urls)
        self._urls_to_visit.update(result)

    def __repr__(self):
        name = self.__class__.__name__
        return f'<{name} urls_to_visit={self.urls_to_visit_count} visited_urls={self.visited_urls_count}>'

    def __iter__(self):
        for url in self._urls_to_visit:
            yield url

    def __contains__(self, url):
        return any([
            str(url) in self._urls_to_visit,
            str(url) in self._visited_urls
        ])

    def __len__(self):
        """Returns the amount of urls
        left to visit"""
        return len(self._urls_to_visit)

    def __getitem__(self, index):
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
        container = OrderedDict()
        for key, values in self._grouped_by_page.items():
            container[key] = list(values)
        return container

    def pre_save(self, urls):
        # final_urls = set()
        # urls = map(lambda x: URL(x), urls)
        # for url in urls:
        #     if url.is_file:
        #         continue
        #     final_urls.add(str(url))
        # return list(final_urls)
        return urls

    def backup(self):
        return {
            'date': str(datetime.datetime.now(tz=pytz.UTC)),
            'urls_to_visit': list(self._urls_to_visit),
            'visited_urls': list(self._visited_urls),
            'statistics': {
                'last_visited_url': str(self._current_url) if self._current_url is not None else None,
                'urls_to_visit_count': self.urls_to_visit_count,
                'visited_urls_count': self.visited_urls_count,
                'total_urls': sum([self.urls_to_visit_count, self.visited_urls_count]),
                'completion_rate': self.completion_rate
            }
        }

    def append(self, url):
        self._seen_urls.add(url)

        if url in self._urls_to_visit:
            return False

        if url in self._visited_urls:
            return False

        self._urls_to_visit.add(url)
        if self.sort_urls:
            self._urls_to_visit = set(sorted(self._urls_to_visit))
            self._visited_urls = set(sorted(self._visited_urls))

    def appendleft(self, url):
        urls_to_visit = list(self._urls_to_visit)
        urls_to_visit.insert(0, url)
        self._urls_to_visit = set(urls_to_visit)

    def clear(self):
        self._urls_to_visit.clear()
        self._visited_urls.clear()

    def reverse(self):
        container = []
        for i in range(self.urls_to_visit_count, 0, -1):
            try:
                container.append(list(self._urls_to_visit)[i - 1])
            except IndexError:
                continue
        self._urls_to_visit = set(container)

    def update(self, urls, current_url=None):
        keys = self._grouped_by_page.keys()
        if keys:
            key = current_url or list(keys)[-1] + 1
        else:
            key = current_url or 1

        for url in urls:
            self._grouped_by_page[key].add(url)
            self.append(url)

    def get(self):
        url = self._urls_to_visit.pop()
        self._current_url = URL(url)
        self._visited_urls.add(url)
        return self._current_url


class URLGenerator:
    """Generates a set of urls using a template

    >>> generator = URLGenerator('http://example.com/$id')
    """

    def __init__(self, template, params={}, k=10, start=0):
        self.base_template_url = Template(template)

        new_params = []
        base_params = [params for _ in range(k)]
        for i, param in enumerate(base_params, start=start):
            new_param = {}
            for key, value in param.items():
                if value == 'number':
                    new_param[key] = i
            new_params.append(new_param)

        self.urls = []
        for i in range(k):
            try:
                self.urls.append(
                    self.base_template_url.substitute(new_params[i])
                )
            except KeyError:
                self.urls.append(template)

    def __iter__(self):
        for url in self.urls:
            yield url

    def __aiter__(self):
        for url in self.urls:
            yield url

    def __len__(self):
        return len(self.urls)


class URLsLoader:
    """Loads a set of urls from a file"""

    def __init__(self):
        self.data = {}
        self._urls_to_visit = []
        self._visited_urls = []

    def __repr__(self) -> str:
        statistics = f'urls_to_visit={len(self._urls_to_visit)} '
        f'visited_urls={len(self._visited_urls)}'
        return f'<URLCache: {statistics}>'

    @property
    def urls_to_visit(self):
        return set(self._urls_to_visit)

    @property
    def visited_urls(self):
        return set(self._visited_urls)

    def load_from_file(self):
        from kryptone.utils.file_readers import read_json_document

        data = read_json_document('cache.json')
        self._urls_to_visit = data['urls_to_visit']
        self._visited_urls = data['visited_urls']
        logger.info(f'Loaded {len(self._urls_to_visit)} urls')
        self.data = data

    def load_from_dict(self, data):
        if not isinstance(data, dict):
            raise ValueError('Data should be a dictionnary')
        self._urls_to_visit = data['urls_to_visit']
        self._visited_urls = data['visited_urls']
        self.data = data
