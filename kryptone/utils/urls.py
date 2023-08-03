import pathlib
import re
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
        return hash([self.raw_url, self.url_object.path])
    
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
        file_extensions = read_document('kryptone/kryptone/data/file_extensions.txt', as_list=True)
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
        as the url to compare"""
        if isinstance(url_to_compare, str):
            url_to_compare = self.create(url_to_compare)

        logic = [
            self.url_object.path == url_to_compare.url_object.path
        ]

        if url_to_compare.url_object.path == '/' and self.url_object.path == '':
            logic.append(True)

        if self.url_object.path == '/' and url_to_compare.url_object.path == '':
            logic.append(True)
        
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


class URLFile:
    urls = []
    def __init__(self, processor=None):
        try:
            data = read_document('urls.txt')
        except:
            logger.info('No urls were loaded from url cache file')
        else:
            urls = data.split('\n')
            if processor is not None:
                for url in urls:
                    self.urls.append(processor(url))

    def __iter__(self):
        return iter(self.urls)
    
    def __str__(self):
        return self.urls


class TestUrl:
    """Test two different urls by checking path
    similarity
    
    >>> TestUrl('https://example.com', 'http://example.com/')
    ... True
    """
    def __init__(self, current_url, url_to_test):
        self.current_url = URL(current_url)
        self.url_to_test = URL(url_to_test)
        self.test_result = self.current_url.compare(url_to_test)

    def __repr__(self):
        return f'<TestUrl: result={self.test_result}>'
    
    def __bool__(self):
        return self.test_result


class URLPassesTest:
    """Checks if an url is able to pass a
    a given test
    
    >>> class Spider(BaseCrawler):
            url_passes_tests = [
                URLPassesTest('/example')
            ]
    """

    def __init__(self, *paths, name=None):
        self.name = name
        self.url = None
        self.paths = set(paths)

    def __call__(self, url):
        result = []
        for path in self.paths:
            if path in self.url.url_object.path:
                result.append(True)
            else:
                result.append(False)
        if any(result):
            logger.warning(f'Url fails test: {self.name}: {url}')
            return False
        return True

    def prepare(self, url):
        self.url = URL(url)
        if self.name is None:
            self.name = f'<URLPassesTest: [{len(self.paths)}]>'
