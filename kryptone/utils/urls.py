import csv
import datetime
import itertools
import json
import pathlib
import re
from collections import OrderedDict, defaultdict
from functools import lru_cache
from string import Template
from urllib.parse import (ParseResult, parse_qs, unquote, urlencode, urljoin,
                          urlparse, urlunparse)

import pandas
import pytz
import requests
from asgiref.sync import sync_to_async

from kryptone import logger
from kryptone.conf import settings
from kryptone.exceptions import NoStartUrlsFile
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_while
from kryptone.utils.randomizers import RANDOM_USER_AGENT


@lru_cache(maxsize=100)
def load_image_extensions():
    try:
        from PIL import Image
    except ImportError:
        return []
    else:
        Image.init()
        return [ext.lower() for ext in Image.EXTENSION]


class URL:
    """Transforms a URL string into a Python object, 
    allowing various operations to be performed 
    on the URL

    >>> url = URL('http://example.com')
    """

    def __init__(self, url, *, domain=None):
        if isinstance(url, URL):
            url = str(url)

        if isinstance(url, ParseResult):
            url = urlunparse((
                url.scheme,
                url.netloc,
                url.path,
                url.query,
                url.params,
                url.fragment
            ))

        if callable(url):
            url = url()

        if url.startswith('/') and domain is not None:
            domain = URL(domain)
            logic = [
                domain.is_path,
                domain.has_path,
                domain.has_queries,
                domain.has_fragment
            ]
            if any(logic):
                raise ValueError(f'Domain is not valid: {domain}')

            url = urljoin(str(domain), url)

        self.raw_url = url
        self.domain = domain
        self.url_object = urlparse(self.raw_url)

    def __repr__(self):
        return f'<URL: {self.raw_url}>'

    def __str__(self):
        return self.raw_url

    def __eq__(self, obj):
        if not isinstance(obj, URL):
            return NotImplemented
        return self.raw_url == obj

    def __add__(self, obj):
        if not isinstance(obj, str):
            return NotImplemented
        return URL(urljoin(self.raw_url, obj))

    def __contains__(self, obj):
        if isinstance(obj, URL):
            return obj.raw_url in self.raw_url
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
    def has_queries(self):
        return self.url_object.query != ''

    @property
    def has_path(self):
        return self.url_object.path != ''

    @property
    def is_image(self):
        return self.as_path.suffix in load_image_extensions()

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

    @property
    def query(self):
        return parse_qs(self.url_object.query)

    @classmethod
    def create(cls, url):
        return cls(url)

    @staticmethod
    def _structural_check(url, domain=None):
        clean_url = unquote(url)
        # if clean_url.startswith('/') and domain is not None:
        #     domain = URL(domain)
        #     clean_url = urlunparse(
        #         domain.url_object.scheme,
        #         domain.url_object.netloc,
        #         url,
        #         None,
        #         None,
        #         None
        #     )
        return clean_url, urlparse(clean_url)

    def rebuild_query(self, **query):
        if self.url_object.query:
            clean_values = {}
            initial_query = parse_qs(self.url_object.query)
            for key, value in initial_query.items():
                clean_values[key] = value[0] if isinstance(
                    value, list) else value
            query = initial_query | clean_values
        string_query = urlencode(query)
        url = self.raw_url + f'?{string_query}'
        return URL(url)

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
        ... instance.test_url(r'a$')
        ... True
        """
        result = re.search(regex, self.raw_url)
        if result:
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

    def __call__(self, url):
        return NotImplemented

    def convert_url(self, url):
        if isinstance(url, URL):
            return url
        return URL(url)


class URLIgnoreTest(BaseURLTestsMixin):
    """The `URLIgnoreTest` class is designed to filter 
    out URLs based on specified paths that should be ignored. 
    If any part of the URL's path matches one or more 
    of the provided paths, the URL will be ignored.

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
    """The URLIgnoreRegexTest class is designed to filter 
    out URLs based on a specified regular expression pattern. 
    If any part of the URL matches the provided regex pattern, 
    the URL will be ignored.

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


class BaseURLGenerator:
    def __len__(self):
        return NotImplemented

    def __iter__(self):
        return self.resolve_generator()

    def __aiter__(self):
        return sync_to_async(self.resolve_generator)()

    def resolve_generator(self):
        return NotImplemented


class URLQueryGenerator(BaseURLGenerator):
    """This class allows you to generate a set of URLs by substituting 
    the value of a specified query parameter with different values. This is 
    useful for creating multiple URLs with varying query parameters based 
    on a base URL.

    It takes a base URL, a query parameter to be substituted, and a list of values 
    for substitution. It generates new URLs by replacing the specified query 
    parameter's value with each value from the provided list.

    >>> instance = URLQueryGenerator('http://example.com?year=2001', param='year', param_values=['2002', '2003'])
    ... instance.resolve_generator()
    ... ['http://example.com?year=2001', 'http://example.com?year=2002', 'http://example.com?year=2003']
    """

    def __init__(self, url, *, param=None, param_values=[], query={}):
        from kryptone.utils.urls import URL

        self.url_instance = URL(url)

        items = []
        for value in param_values:
            items.append({param: value})

        self.query = query
        self.generated_params = items

    def __len__(self):
        return len(self.resolve_generator())

    def resolve_generator(self):
        for item in self.generated_params:
            full_query = item | self.query
            query = urlencode(full_query)
            yield str(self.url_instance) + f'?{query}'


class URLPathGenerator(BaseURLGenerator):
    """This class generates a set of URLs by substituting values 
    into a URL path template. This is useful for creating multiple URLs 
    with varying path parameters based on a template.

    It takes an URL template, a dictionary of parameters, and generates a set of URLs 
    by replacing template variables with sequential values. The primary use case is 
    generating URLs where a part of the path changes according to a 
    specified pattern, such as incrementing numbers.

    >>> generator = URLPathGenerator('http://example.com/$id', params={'id': 'number'}, k=2)
    ... ['http://example.com/1', 'http://example.com/2']
    """

    def __init__(self, template, params={}, k=10, start=0):
        self.base_template_url = Template(template)
        self.params = params
        self.k = k
        self.start = start

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.__len__()}>'

    def __len__(self):
        return len(list(self.resolve_generator()))

    def resolve_generator(self):
        new_params = []
        base_params = [self.params for _ in range(self.k)]
        for i, param in enumerate(base_params, start=self.start):
            new_param = {}
            for key, value in param.items():
                if value == 'number' or value == 'k':
                    new_param[key.removeprefix('$')] = i
            new_params.append(new_param)

        for i in range(self.k):
            try:
                yield self.base_template_url.substitute(new_params[i])
            except KeyError:
                yield self.base_template_url


class URLPaginationGenerator(BaseURLGenerator):
    """This class generates a set of URLs by adding a pagination query parameter 
    to a base URL. This is useful for creating URLs that correspond to different 
    pages of a paginated website.

    It takes a base URL and a pagination query parameter name, and generates a 
    set of URLs with the pagination parameter incremented sequentially. This allows for the 
    creation of multiple URLs to explore different pages of a paginated website.

    >>> PagePaginationGenerator('http:////example.com', k=2)
    ... ['http:////example.com?page=1', 'http:////example.com?page=2']
    """

    def __init__(self, url, param_name='page', k=10):
        self.urls = []
        self.final_urls = []

        if isinstance(url, str):
            url = URL(url).remove_fragment()

        if isinstance(k, float):
            k = int(k)

        if param_name in url.query:
            pass

        self.url = url
        self.param_name = param_name
        self.k = k

    def __repr__(self):
        return f'<{self.__class__.__name__}: {len(self.final_urls)}>'

    def __len__(self):
        return len(self.final_urls)

    def resolve_generator(self):
        url = str(self.url)

        for _ in range(self.k):
            self.urls.append(url)

        counter = 1
        for url in self.urls:
            final_query = urlencode(
                {self.param_name: str(counter)},
                encoding='utf-8'
            )
            yield url + f'?{final_query}'
            counter = counter + 1


class MultipleURLManager:
    """This class allows the management for multiple urls
    by removing currently visited urls from urls to visit
    and therefore making it easier for the robot to move
    from an url to another with ease
    """
    _urls_to_visit = set()
    _visited_urls = set()
    _seen_urls = set()
    _grouped_by_page = defaultdict(set)
    _current_url = None

    def __init__(self, start_urls=[], start_url=None, sort_urls=False, convert_objects=False):
        if start_url is None:
            start_url = URL(start_urls[0])
        self.start_url = start_url

        df = pandas.DataFrame({'urls': start_urls})
        df['visited'] = False
        df['visited_on'] = None
        self.dataframe = df

        if sort_urls:
            self.dataframe = self.dataframe.sort_values('urls')

        self.sort_urls = sort_urls
        # start_urls
        result = self.pre_save(self.dataframe.urls.to_list())
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

    @lru_cache(maxsize=100)
    def all_urls(self):
        return list(itertools.chain(
            self._visited_urls,
            self._urls_to_visit
        ))

    def url_structural_check(self, url):
        """Checks the structure of an
        incoming url. When the the string
        is a path, it is readapted to suit
        the expected pattern of an url"""
        url = str(url)
        clean_url = unquote(url)
        if url.startswith('/'):
            clean_url = self.urljoin(clean_url)
        return clean_url, urlparse(clean_url)

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

    def pre_append(self, urls):
        pass

    def append_multiple(self, urls):
        counter = 0
        valid_urls = set()
        invalid_urls = set()

        for url in urls:
            state = self.append(url)
            if state:
                valid_urls.add(url)
                continue
            counter = counter + 1
            invalid_urls.add(url)
        return valid_urls, invalid_urls

    def append(self, url):
        if url is None:
            return False

        clean_url = URL(url)
        self._seen_urls.add(url)

        if url in self._visited_urls:
            return False

        if url in self._urls_to_visit:
            return False

        if (clean_url.url_object.netloc == '' or
                clean_url.url_object.path == ''):
            return False

        self._urls_to_visit.add(url)
        new_urls = pandas.DataFrame({'urls': [url]})
        self.dataframe = pandas.concat([self.dataframe, new_urls])

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

        found_urls = self.dataframe[self.dataframe.urls == url]
        for item in found_urls.itertuples():
            self.dataframe.loc[item.Index, 'visited'] = True
            self.dataframe.loc[item.Index, 'visited_on'] = get_current_date()
        return self._current_url


class LoadStartUrls(BaseURLGenerator):
    """The class loads start URLs from a CSV or JSON file 
    to be used by a web crawler. This allows for automated operations on 
    the pages specified by these URLs

    The class takes a filename (without the extension) and a flag indicating 
    whether the file is in JSON format. It then loads the URLs from the 
    specified file and makes them available for the crawler.

    >>> class MyCrawler(SiteCrawler):
    ...     class Meta:
    ...         start_urls = LoadStartUrls()
    """

    def __init__(self, *, filename=None, is_json=False):
        self.is_json = is_json
        extension = 'json' if self.is_json else 'csv'
        self.filename = f"{filename or 'start_urls'}.{extension}"

    def resolve_generator(self):
        try:
            path = settings.PROJECT_PATH / self.filename
            with open(path, mode='r', encoding='utf-8') as f:
                if self.is_json:
                    data = json.load(f)
                    yield from list(set(item['url'] for item in data))
                else:
                    yield from list(itertools.chain(*csv.reader(f)))
        except FileNotFoundError:
            raise NoStartUrlsFile()
