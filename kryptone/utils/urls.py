import pathlib
import re
from functools import lru_cache
from urllib.parse import urljoin, urlparse

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
        return self.raw_url.startswith('http')

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

    def test_path(self, regex):
        """Test if the url's path passes test

        >>> instance = URL('http://example.com/a')
        ... instance.test_path(r'\/a')
        ... True
        """
        result = re.search(regex, self.raw_url)
        if result:
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


class TestUrl:
    """Test two different urls by checking path
    similarity

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


class URLPassesTest:
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

    def __init__(self, name, *, paths=[], ignore_files=[]):
        self.name = name
        self.paths = set(paths)
        self.failed_paths = []
        self.ignore_files = ignore_files

    def __call__(self, url):
        result = []

        if isinstance(url, str):
            url = URL(url)

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


class UrlPassesRegexTest:
    """Checks if an url is able to pass a
    a given test

    >>> class Spider(BaseCrawler):
            url_passes_tests = [
                UrlPassesRegexTest(
                    'simple_test',
                    regex=r'\/a$'
                )
            ]
    """

    def __init__(self, name, *, regex=None):
        self.name = name
        self.regex = re.compile(regex)

    def __call__(self, url):
        if self.regex.search(url):
            return True
        logger.warning(f"{url} failed test: '{self.name}'")
        return False
