from collections import defaultdict
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
        return URL(urljoin(self.raw_url, obj))

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

    @property
    def is_secured(self):
        return self.url_object.scheme == 'https'

    @classmethod
    def create(cls, url):
        return cls(url)
    
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

    # def paginate(self, k=10, regex_path=None, param=None):
    #     """Increase the pagination number provided
    #     on a given url"""
    #     if regex_path is None and param is None:
    #         # If we have nothing, classically, page
    #         # is used to paginate in urls
    #         param = 'page'
    #     return 1


class BaseURLTestsMixin:
    blacklist = set()
    blacklist_distribution = defaultdict(list)
    error_message = "{url} was blacklisted by filter '{filter_name}'"

    def __call__(self, url):
        pass

    def convert_url(self, url):
        if isinstance(url, URL):
            return url
        return URL(url)


class URLIgnoreTest(BaseURLTestsMixin):
    """Ignore every url in which the provided
    paths match one or many sections of the url

    For example, `example.com/1` will be 
    ignored with `/1`
    """

    def __init__(self, name, *, paths=[]):
        self.name = name
        if not isinstance(paths, (list, tuple)):
            raise ValueError("'paths' should be a list or a tuple")
        self.paths = set(paths)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.paths}>'

    def __call__(self, url):
        exclusion_truth_array = []

        url = self.convert_url(url)
        
        # Include all the urls that match
        # the path to exclude as True and the
        # others as False
        for path in self.paths:
            if path in url.url_object.path:
                self.blacklist.add(path)
                exclusion_truth_array.append(True)
            else:
                exclusion_truth_array.append(False)

        if any(exclusion_truth_array):
            logger.warning(
                self.error_message.format(
                    url=url, 
                    filter_name=self.name
                )
            )
            return True
        return False


class URLIgnoreRegexTest(BaseURLTestsMixin):
    """Ignore every url in which the provided
    regex path match a specific section of the url

    For example, `example.com/1` will be 
    ignored with `\/\d+`
    """

    def __init__(self, name, regex):
        self.name = name
        self.regex = re.compile(regex)

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.regex}]>'

    def __call__(self, url):
        result = self.regex.search(url)
        if result:
            logger.warning(
                self.error_message.format(
                    url=url, 
                    filter_name=self.name
                )
            )
            return True
        return False


# class URLPassesRegexTest(BaseURLTestsMixin):
#     """Only include and keep urls that successfully pass
#     the provided regex test
#     """

#     def __init__(self, name, regex):
#         self.name = name
#         self.regex = re.compile(regex)

#     def __repr__(self):
#         return f'<{self.__class__.__name__} [{self.regex}]>'

#     def __call__(self, url):
#         result = self.regex.search(url)
#         if result:
#             # Indicate to not ignore
#             # the url
#             return False
#         logger.warning(
#             self.error_message.format(
#                 url=url, 
#                 filter_name=self.name
#             )
#         )
#         return True
