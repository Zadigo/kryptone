import re
from collections import defaultdict


from internal_types import TypeUrl
from kryptone import logger
from kryptone.utils.urls.base import URL


class BaseURLTestsMixin[U: URL]:
    blacklist: set[U] = set()
    blacklist_distribution: defaultdict[str, list[U]] = defaultdict(list)
    error_message: str = "{url} was blacklisted by filter '{filter_name}'"

    def __call__(self, url: U):
        return NotImplemented

    def convert_url(self, url: U) -> U:
        if isinstance(url, URL):
            return url
        return URL(url)


class URLIgnoreTest(BaseURLTestsMixin[URL]):
    """The `URLIgnoreTest` class is designed to filter
    out URLs based on specified paths that should be ignored.
    If any part of the URL's path matches one or more
    of the provided paths, the URL will be ignored.

    For example, `example.com/1` will be
    ignored with `/1`

    Args:
        name (str): The name of the filter for logging purposes.
        paths (list[str] | tuple[str]): A list or tuple of paths to be ignored.
    """

    def __init__(self, name: str, *, paths: list[str] | tuple[str] = []):
        self.name = name
        if not isinstance(paths, (list, tuple)):
            raise ValueError("'paths' should be a list or a tuple")
        self.paths = set(paths)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.paths}>"

    def __call__(self, url: str | URL):
        exclusion_truth_array = []

        url = self.convert_url(url)

        # Include all the urls that match
        # the path to exclude as True and the
        # others as False
        for path in self.paths:
            if path in str(url.url_object.path):
                self.blacklist.add(path)
                exclusion_truth_array.append(True)
            else:
                exclusion_truth_array.append(False)

        if any(exclusion_truth_array):
            logger.warning(self.error_message.format(url=url, filter_name=self.name))
            return True
        return False


class URLIgnoreRegexTest(BaseURLTestsMixin):
    """The URLIgnoreRegexTest class is designed to filter
    out URLs based on a specified regular expression pattern.
    If any part of the URL matches the provided regex pattern,
    the URL will be ignored.

    For example, `example.com/1` will be
    ignored with `\\d+`
    """

    def __init__(self, name: str, regex: str):
        self.name = name
        self.regex = re.compile(regex)

    def __repr__(self):
        return f"<{self.__class__.__name__} [{self.regex}]>"

    def __call__(self, url: TypeUrl):
        result = self.regex.search(str(url))
        if result:
            logger.warning(self.error_message.format(url=url, filter_name=self.name))
            return True
        return False
