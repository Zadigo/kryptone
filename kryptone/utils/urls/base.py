import pathlib
import re
from functools import cached_property, lru_cache
from typing import Callable, Optional, Union
from urllib.parse import (
    ParseResult,
    parse_qs,
    unquote,
    unquote_plus,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests

from internal_types import TypeUrl
from kryptone.conf import settings
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_while
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.internal_types import TypeUrl


@lru_cache(maxsize=100)
def load_image_extensions() -> list[str]:
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
    on the URL::

        url = URL('http://example.com')

    Check domain::

        url.is_same_domain('http://example.com')  # True

    Capture a value in the url::

        url.capture(r'\/a')  # returns a match object

    Test the path against a regex::

        url.multi_test_path([r'<pattern>'], operator="and")  # True

    Args:
        url (Union[str, URL, ParseResult]): The URL to be transformed into a URL object.
        domain (Optional[Union[URL, str]]): An optional domain to be used for relative URLs.
    """

    def __init__(
        self,
        url: Union[TypeUrl, Callable[[], str], None],
        *,
        domain: Optional[Union["URL", str]] = None,
    ):
        self.invalid_initial_check = False

        if isinstance(url, URL):
            url = str(url)

        if isinstance(url, ParseResult):
            url = urlunparse(
                (url.scheme, url.netloc, url.path, url.query, url.params, url.fragment)
            )

        if callable(url):
            url = url()

        if url is None:
            self.invalid_initial_check = True
            url = ""
        elif isinstance(url, (int, float)):
            self.invalid_initial_check = True
            url = str(url)

        if url.startswith("/") and domain is not None:
            domain = URL(url=domain)
            logic = [
                domain.is_path,
                domain.has_path,
                domain.has_query,
                domain.has_fragment,
            ]
            if any(logic):
                raise ValueError(f"Domain is not valid: {domain}")

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
        return f"<URL: {self.raw_url}>"

    def __str__(self):
        return self.raw_url or ""

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
        return all([not self.is_valid, not self.raw_url == ""])

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
        path = settings.GLOBAL_KRYPTONE_PATH / "data/file_extensions.txt"
        return read_document(path, as_list=True)

    @property
    def is_social_link(self):
        if self.is_empty:
            return False

        return any(
            [
                "facebook.com" in self.raw_url,
                "twitter.com" in self.raw_url,
                "tiktok.com" in self.raw_url,
                "snapchat.com" in self.raw_url,
                "youtube.com" in self.raw_url,
                "pinterest.com" in self.raw_url,
                "spotify.com" in self.raw_url,
            ]
        )

    @property
    def is_empty(self):
        return any([self.raw_url == "", self.raw_url is None])

    @property
    def is_path(self):
        if self.is_empty:
            return False
        return self.raw_url.startswith("/")

    # @property
    # def is_image(self):
    #     if self.is_empty:
    #         return False

    #     if self.as_path.suffix != '':
    #         suffix = self.as_path.suffix.removeprefix('.')
    #         if suffix in constants.IMAGE_EXTENSIONS:
    #             return True
    #     return False

    @property
    def is_valid(self):
        if self.is_empty:
            return False

        return any(
            [
                self.raw_url.startswith("http://"),
                self.raw_url.startswith("https://"),
                self.invalid_initial_check,
            ]
        )

    @property
    def has_fragment(self):
        if self.is_empty:
            return False

        return any([self.url_object.fragment != "", self.raw_url.endswith("#")])

    @property
    def as_dict(self):
        if self.is_empty:
            return {}

        return {"url": self.raw_url, "is_valid": self.is_valid}

    @property
    def has_path(self):
        if self.is_empty:
            return False

        return self.url_object.path != ""

    @property
    def has_query(self):
        if self.is_empty:
            return False

        return self.url_object.query != ""

    @property
    def is_image(self):
        if self.is_empty or self.as_path is None:
            return False

        return self.as_path.suffix in load_image_extensions()

    @property
    def is_file(self):
        if self.is_empty or self.as_path is None:
            return False

        extension = self.as_path.suffix

        if extension == "":
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
            return pathlib.Path(unquote_plus(str(self.url_object.path)))

        clean_path = unquote_plus(self.raw_url)
        return pathlib.Path(clean_path)

    @property
    def url_path(self):
        if self.is_empty:
            return None

        return unquote_plus(str(self.url_object.path))

    @property
    def get_extension(self):
        if self.is_empty or self.as_path is None:
            return None

        if self.is_file:
            return self.as_path.suffix
        return None

    @property
    def url_stem(self):
        if self.is_empty or self.as_path is None:
            return None

        return self.as_path.stem

    @property
    def is_secured(self):
        if self.is_empty:
            return False

        return self.url_object.scheme == "https"

    @property
    def query(self):
        if self.is_empty:
            return None

        return parse_qs(str(self.url_object.query))

    @property
    def get_filename(self):
        """If the url points to a file, try to
        return it's actual name"""
        if self.as_path is None:
            return None

        if self.is_file:
            return self.as_path.name
        return None

    @classmethod
    def create(cls, url: str):
        return cls(url)

    @staticmethod
    def structural_check(
        url: TypeUrl, domain: Optional[TypeUrl] = None
    ):
        clean_url = unquote(str(url))
        return clean_url, urlparse(clean_url)

    def rebuild_query(self, **query: str):
        """Creates a new instance of the url
        with the existing query and and key/value
        parameters of the query parameter"""
        if self.has_query:
            clean_values = {}

            for key, value in self.query.items():
                if isinstance(value, list):
                    clean_values[key] = ",".join(value)
                    continue

                clean_values[key] = value

            query = query | clean_values

        string_query = urlencode(query)
        url = urlunparse(
            (
                self.url_object.scheme,
                self.url_object.netloc,
                self.url_object.path,
                None,
                string_query,
                None,
            )
        )
        return URL(url)

    def is_same_domain(self, url: Union[str, "URL", None]) -> bool:
        """Checks that an incoming url is the same
        domain as the current one::

            url = URL('http://example.com')
            url.is_same_domain('http://example.com') # True
        """
        if url is None:
            return False

        if isinstance(url, str):
            url = URL(url)
        return url.url_object.netloc == self.url_object.netloc

    def get_status(self):
        headers = {"User-Agent": RANDOM_USER_AGENT()}
        response = requests.get(self.raw_url, headers=headers)
        return response.ok, response.status_code

    def compare(self, url_to_compare: TypeUrl) -> bool:
        """Checks that the given url has the same path
        as the url to compare::

            instance = URL('http://example.com/a')
            instance.compare('http://example.com/a')
        """
        if isinstance(url_to_compare, str):
            url_to_compare = self.create(url_to_compare)

        logic = [
            self.url_object.path == url_to_compare.url_object.path,
            url_to_compare.url_object.path == "/" and self.url_object.path == "",
            self.url_object.path == "/" and url_to_compare.url_object.path == "",
        ]
        return any(logic)

    def capture(self, regex: str):
        """Captures a value in the
        provided url::

            instance = URL('http://example.com/a')
            result = instance.capture(r'\/a')
            result.group(1) # "/a"
        """
        result = re.search(regex, self.raw_url)
        if result:
            return result
        return False

    def test_url(self, regex: str):
        """Test if an element in the url passes test. The
        whole url is used to perform the test::

            instance = URL('http://example.com/a')
            instance.test_url(r'a$') # True
        """
        result = re.search(regex, self.raw_url)
        if result:
            return True
        return False

    def test_path(self, regex: str):
        """Test if the url's path passes test. Only the
        path is used to perform the test::

            instance = URL('http://example.com/a')
            instance.test_path(r'\/a') # True
        """
        path_search = re.search(regex, str(self.url_object.path))
        if path_search:
            return True
        return False

    def multi_test_path(self, regexes: list[str], operator: str = "and"):
        """Test if the url's path passes test. Only the
        path is used to perform the test::

            instance = URL('http://example.com/a')
            instance.multi_test_path([r'\\a', r'\\b']) # True
        """
        truth_array = []
        for regex in regexes:
            truth_array.append(self.test_path(regex))

        if operator == "and":
            return all(truth_array)
        elif operator == "or":
            return any(truth_array)
        else:
            raise ValueError("Operator is not valid")

    def decompose_path(self, exclude: list[str] = []):
        """Decomposes an url's path into a list of values. The exclude parameter
        allows you to exclude certain values from the list::

            instance = URL('http://example.com/a/b')
            instance.decompose_path(exclude=[]) # ["a", "b"]
        """
        result = self.url_object.path.split("/")

        def clean_values(value: str):
            if value == "":
                return True

            if exclude and value in exclude:
                return True

            return False

        return list(drop_while(clean_values, result))

    def remove_fragment(self):
        """Reconstructs the url without the fragment
        if it is present but keeps the queries::

            url = URL('http://example.com#')
            url.reconstruct() # http://example.com
        """
        clean_url = urlunparse(
            (
                self.url_object.scheme,
                self.url_object.netloc,
                self.url_object.path,
                None,
                None,
                None,
            )
        )
        if self.has_fragment:
            return self.create(clean_url)
        return self
