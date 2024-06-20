import pathlib
import re
import secrets
from collections import defaultdict
from functools import cached_property
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests

from kryptone import constants, logger
from kryptone.conf import settings
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_while
from kryptone.utils.randomizers import RANDOM_USER_AGENT


class URL:
    """Represents an url

    >>> instance URL('http://example.com')
    """

    def __init__(self, url_string):
        if isinstance(url_string, URL):
            self.raw_url = url_string.raw_url
            self.url_object = url_string.url_object
        else:
            self.raw_url = unquote(url_string or '')
            self.url_object = urlparse(self.raw_url)

    def __repr__(self):
        return f'<URL: {self.raw_url}>'

    def __str__(self):
        return self.raw_url

    def __eq__(self, obj):
        return self.raw_url == obj

    def __add__(self, obj):
        return URL(urljoin(self.raw_url, obj))

    # def __and__(self, obj):
    #     return all([
    #         self.raw_url != '',
    #         self.is_valid,
    #         obj.raw_url != '',
    #         obj.is_valid == True
    #     ])

    def __invert__(self):
        return all([
            not self.is_valid,
            not self.raw_url == ''
        ])

    # def __or__(self, obj):
    #     if not isinstance(obj, URL):
    #         obj = URL(obj)
    #     invalid_state = any([
    #         self.raw_url == '',
    #         self.is_valid == False
    #     ])
    #     return obj if invalid_state else self

    def __contains__(self, obj):
        return obj in self.raw_url

    def __hash__(self):
        return hash((self.raw_url, self.url_object.path))

    def __len__(self):
        return len(self.raw_url)

    @cached_property
    def _file_extensions(self):
        path = settings.GLOBAL_KRYPTONE_PATH / 'data/file_extensions.txt'
        return read_document(path, as_list=True)

    @property
    def is_social_link(self):
        return any([
            'facebook.com' in self.raw_url,
            'twitter.com' in self.raw_url,
            'tiktok.com' in self.raw_url,
            'snapchat.com' in self.raw_url,
            'youtube.com' in self.raw_url,
            'pinterest.com' in self.raw_url,
            'spotify.com' in self.raw_url
        ])

    @property
    def is_empty(self):
        return any([
            self.raw_url == '',
            self.url_object.netloc == '' and self.url_object.path == ''
        ])

    @property
    def is_path(self):
        return self.raw_url.startswith('/')

    @property
    def is_image(self):
        if self.as_path.suffix != '':
            suffix = self.as_path.suffix.removeprefix('.')
            if suffix in constants.IMAGE_EXTENSIONS:
                return True
        return False

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
    def as_dict(self):
        return {
            'url': self.raw_url,
            'is_valid': self.is_valid
        }

    @property
    def is_file(self):
        extension = self.as_path.suffix

        if extension == '':
            return False

        if self.as_path.suffix in self._file_extensions:
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

    def has_queries(self):
        return self.url_object.query != ''

    def is_same_domain(self, url):
        """Checks that an incoming url is the same
        domain as the current one

        >>> url = URL('http://example.com')
        ... url.is_same_domain('http://example.com')
        ... True
        """
        if isinstance(url, str):
            url = URL(url)
        return url.url_object.netloc == self.url_object.netloc

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

    def remove_fragment(self):
        """Reconstructs the url without the fragment
        if it is present but keeps the queries

        >>> url = URL('http://example.com#')
        ... url.reconstruct()
        ... 'http://example.com'
        """
        clean_url = urlunparse((
            self.url_object.scheme,
            self.url_object.netloc,
            self.url_object.path,
            None,
            None,
            None
        ))
        if self.has_fragment:
            return self.create(clean_url)
        return self


class BaseURLTestsMixin:
    blacklist = set()
    blacklist_distribution = defaultdict(list)
    error_message = "{url} was blacklisted by filter '{filter_name}'"

    def __init__(self, name):
        name = str(name).lower().replace(' ', '_')
        self.name = f'ignore_{name}_{secrets.token_hex(nbytes=5)}'

    def __call__(self, url):
        pass

    def __hash__(self):
        return hash((self.name))

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
        super().__init__(name)
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
        super().__init__(name)
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
