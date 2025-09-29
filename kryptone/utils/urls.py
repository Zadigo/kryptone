import csv
import datetime
import itertools
import json
import pathlib
import re
from collections import OrderedDict, defaultdict
from functools import cached_property, lru_cache
from string import Template
from urllib.parse import (ParseResult, parse_qs, unquote, unquote_plus, urlencode, urljoin,
                          urlparse, urlunparse)

import pandas
import pytz
import requests
from asgiref.sync import sync_to_async

from kryptone import constants, logger
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

    def __init__(self, url: str | 'URL', *, domain=None):
        self.invalid_initial_check = False

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

        if url is None:
            self.invalid_initial_check = True
        elif isinstance(url, (int, float)):
            self.invalid_initial_check = True
            url = str(url)
        else:
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

        try:
            # Try to parse the url even though it's
            # invalid.
            self.url_object = urlparse(self.raw_url)
        except ValueError:
            self.url_object = urlparse(None)
            self.invalid_initial_check = True

    def __repr__(self):
        return f'<URL: {self.raw_url}>'

    def __str__(self):
        return self.raw_url or ''

    def __eq__(self, obj):
        if not isinstance(obj, URL):
            return NotImplemented
        return self.url_object == obj.url_object

    def __lt__(self, obj):
        if not isinstance(obj, URL):
            return NotImplemented
        return self.raw_url < obj.raw_url

    def __gt__(self, obj):
        if not isinstance(obj, URL):
            return NotImplemented
        return self.raw_url > obj.raw_url

    def __lte__(self, obj):
        if not isinstance(obj, URL):
            return NotImplemented
        return self.raw_url <= obj.raw_url

    def __gte__(self, obj):
        if not isinstance(obj, URL):
            return NotImplemented
        return self.raw_url >= obj.raw_url

    def __add__(self, obj):
        if not isinstance(obj, str):
            return NotImplemented
        return URL(urljoin(self.raw_url, obj))

    def __invert__(self):
        return all([
            not self.is_valid,
            not self.raw_url == ''
        ])

    def __contains__(self, obj):
        if isinstance(obj, URL):
            return obj.raw_url in self.raw_url
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
        if self.is_empty:
            return False
        
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
            self.raw_url is None
        ])

    @property
    def is_path(self):
        if self.is_empty:
            return False
        return self.raw_url.startswith('/')

    @property
    def is_image(self):
        if self.is_empty:
            return False
        
        if self.as_path.suffix != '':
            suffix = self.as_path.suffix.removeprefix('.')
            if suffix in constants.IMAGE_EXTENSIONS:
                return True
        return False

    @property
    def is_valid(self):
        if self.is_empty:
            return False

        return any([
            self.raw_url.startswith('http://'),
            self.raw_url.startswith('https://'),
            self.invalid_initial_check
        ])

    @property
    def has_fragment(self):
        if self.is_empty:
            return False
        
        return any([
            self.url_object.fragment != '',
            self.raw_url.endswith('#')
        ])

    @property
    def as_dict(self):
        if self.is_empty:
            return {}
        
        return {
            'url': self.raw_url,
            'is_valid': self.is_valid
        }

    @property
    def has_path(self):
        if self.is_empty:
            return False
        
        return self.url_object.path != ''

    @property
    def has_query(self):
        if self.is_empty:
            return False
        
        return self.url_object.query != ''

    @property
    def is_image(self):
        if self.is_empty:
            return False
        
        return self.as_path.suffix in load_image_extensions()

    @property
    def is_file(self):
        if self.is_empty:
            return False
        
        extension = self.as_path.suffix

        if extension == '':
            return False

        if self.as_path.suffix in self._file_extensions:
            return True
        return False

    @property
    def as_path(self):
        if self.is_empty:
            return None
        
        # Rebuild the url without the query
        # part since it's not important for
        # the path resolution
        if self.has_query:
            return pathlib.Path(unquote_plus(self.url_object.path))

        clean_path = unquote_plus(self.raw_url)
        return pathlib.Path(clean_path)

    @property
    def url_path(self):
        if self.is_empty:
            return None
        
        return unquote_plus(self.url_object.path)

    @property
    def get_extension(self):
        if self.is_empty:
            return None
        
        if self.is_file:
            return self.as_path.suffix
        return None

    @property
    def url_stem(self):
        if self.is_empty:
            return None
        
        return self.as_path.stem

    @property
    def is_secured(self):
        if self.is_empty:
            return False
        
        return self.url_object.scheme == 'https'

    @property
    def query(self):
        if self.is_empty:
            return None
        
        return parse_qs(self.url_object.query)

    @property
    def get_filename(self):
        """If the url points to a file, try to
        return it's actual name """
        if self.is_file:
            return self.as_path.name
        return None

    @classmethod
    def create(cls, url):
        return cls(url)

    @staticmethod
    def structural_check(url, domain=None):
        clean_url = unquote(url)
        return clean_url, urlparse(clean_url)

    def rebuild_query(self, **query):
        """Creates a new instance of the url
        with the existing query and and key/value
        parameters of the query parameter"""
        if self.has_query:
            clean_values = {}

            for key, value in self.query.items():
                if isinstance(value, list):
                    clean_values[key] = ','.join(value)
                    continue

                clean_values[key] = value

            query = query | clean_values

        string_query = urlencode(query)
        url = urlunparse((
            self.url_object.scheme,
            self.url_object.netloc,
            self.url_object.path,
            None,
            string_query,
            None
        ))
        return URL(url)

    def is_same_domain(self, url: str | 'URL'):
        """Checks that an incoming url is the same
        domain as the current one

        >>> url = URL('http://example.com')
        ... url.is_same_domain('http://example.com')
        ... True
        """
        if url is None:
            return False

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

    def capture(self, regex: str):
        """Captures a value in the given url

        >>> instance = URL('http://example.com/a')
        ... result = instance.capture(r'\/a')
        ... result.group(1)
        ... "/a"
        """
        result = re.search(regex, self.raw_url)
        if result:
            return result
        return False

    def test_url(self, regex: str):
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

    def test_path(self, regex: str):
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

    def multi_test_path(self, regexes, operator='and'):
        """Test if the url's path passes test. Only the
        path is used to perform the test

        >>> instance = URL('http://example.com/a')
        ... instance.multi_test_path([r'\/a', r'\/b'])
        ... True
        """
        truth_array = []
        for regex in regexes:
            truth_array.append(self.test_path(regex))
        
        if operator == 'and':
            return all(truth_array)
        elif operator == 'or':
            return any(truth_array)
        else:
            raise ValueError('Operator is not valid')

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
        result = self.regex.search(str(url))
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

    >>> instance = URLQueryGenerator('http://example.com?year=2001', param='year', initial_value=2001, end_value=2003)
    ... instance.resolve_generator()
    ... ['http://example.com?year=2001', 'http://example.com?year=2002', 'http://example.com?year=2003']
    """

    def __init__(self, url, *, param=None, initial_value=0, end_value=0, step=1, param_type='number', query={}):
        acceptable_types = ['number', 'letter']

        if param_type not in acceptable_types:
            raise ValueError('Valid parameter types are: number, letter')

        self.url_instance = URL(url)
        self.parameter_type = param_type
        self.query = self.check_initial_query(query)

        self.initial_value = initial_value
        self.end_value = end_value
        self.step = step
        self.param = param

    def __len__(self):
        return len(self.resolve_generator())

    @staticmethod
    def check_initial_query(query):
        """Function that checks if a value of the
        query dict is None and replaces it with an
        empty string"""
        clean_query = {}
        for key, value in query.items():
            if value is None:
                clean_query[key] = ''
                continue
            clean_query[key] = value
        return clean_query

    def resolve_generator(self):
        if self.parameter_type == 'number':
            calculated_range = 0
            if self.initial_value < 0 or self.end_value < 0:
                raise ValueError('End value cannot be below initial value')

            calculated_range = self.end_value - self.initial_value
            for i in range(calculated_range):
                if (i % self.step) == 0:
                    value = self.initial_value + i

                    full_query = self.query | {self.param: value}
                    query = urlencode(full_query)

                    yield URL(str(self.url_instance) + f'?{query}')

        if self.parameter_type == 'letter':
            pass


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
    _grouped_by_page = defaultdict(set)
    _current_url = None
    list_of_seen_urls = set()
    custom_url_filters = []

    def __init__(self, ignore_images=True, sort_urls=False):
        self.start_url = None
        self.ignore_images = ignore_images
        self.sort_urls = sort_urls
        # This attribute is updated every time
        # "get" is called on the class
        self.current_iteration = 0
        self.dataframe: pandas.DataFrame = None

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

    def urljoin(self, path):
        if self.start_url is None:
            raise Exception(
                'You should call populate at least once '
                'in order to join paths to their base domain'
            )
        return URL(urljoin(str(self.start_url), str(path)))

    def add_urls(self, urls, refresh=False):
        """Manually add urls to the current urls to
        visit list. This is useful for cases where urls are
        nested in other elements than links and that
        cannot actually be retrieved by the spider

        * Runs `self.check_urls` on each url
        * RUns user custom url filters `self.run_url_filters`
        * Updates `self.urls_to_visit`"""
        checked_urls = self.check_urls(urls, refresh=refresh)
        filtered_urls = self.run_url_filters(checked_urls)
        self._urls_to_visit.update(filtered_urls)

        if self.start_url is not None:
            container = self._grouped_by_page[self.start_url]
            container.update(filtered_urls)

    def run_url_filters(self, valid_urls):
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

            logger.info(
                f"Filters completed. {len(urls_removed)} "
                "url(s) removed"
            )
            return urls_kept
        return valid_urls

    def check_urls(self, urls, refresh=False):
        raw_urls = set(urls)

        if self.current_iteration > 0:
            logger.info(f"Found {len(raw_urls)} url(s) in total on this page")

        raw_urls_objs = list(map(lambda x: URL(x), raw_urls))

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
                self.current_iteration > 0
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

    def clear(self):
        self._urls_to_visit.clear()
        self._visited_urls.clear()

    def reverse(self):
        return list(reversed(self.urls_to_visit))

    def get(self):
        """Gets an url from the list of urls to visit.
        This is a destructive function, in other words,
        when the function is called, it removed from the
        list of urls to visit"""
        if not self._urls_to_visit:
            return None

        url = self._urls_to_visit.pop()
        self._current_url = URL(url)
        self._visited_urls.add(url)

        if self.dataframe is not None:
            found_urls = self.dataframe[self.dataframe.urls == url]
            for item in found_urls.itertuples():
                self.dataframe.loc[item.Index, 'visited'] = True
                self.dataframe.loc[item.Index, 'visited_on'] = get_current_date()
            self.current_iteration += 1
            return url
        return None

    def populate(self, start_urls):
        """Function that populates the `urls_to_visit` and
        sets `start_url`. If called more than once, the other
        calls will have no effect"""
        if self.start_url is None:
            start_url = URL(start_urls[0])
            if start_url.is_path:
                raise ValueError(
                    "The first url in the list of startin urls is a path "
                    "you need to implement a valid url string as a "
                    "fist value in the list"
                )
            self.start_url = start_url
            self.add_urls(start_urls)

            self.dataframe = pandas.DataFrame(
                {
                    'urls': list(self.urls_to_visit)
                }
            )
            self.dataframe['visited'] = False
            self.dataframe['visited_on'] = None

            if self.sort_urls:
                self.dataframe = self.dataframe.sort_values('urls')

            result = self.dataframe.urls.to_list()
            self._urls_to_visit.update(result)


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

    The class can also laod urls from the internet by running a request
    to an api endpoint
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
                    for item in data:
                        if isinstance(item, dict):
                            yield item['url']

                        if isinstance(item, str):
                            yield item
                else:
                    yield from list(itertools.chain(*csv.reader(f)))
        except FileNotFoundError:
            raise NoStartUrlsFile()
