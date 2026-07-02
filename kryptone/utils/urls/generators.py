import abc
from string import Template
from typing import Optional, override
from urllib.parse import (
    urlencode,
)

from asgiref.sync import sync_to_async

from kryptone.utils.urls.base import URL
from kryptone.internal_types import TypeUrl


class BaseURLGenerator[U: URL](abc.ABC):
    def __len__(self) -> int:
        return NotImplemented

    def __iter__(self):
        return self.resolve_generator()

    def __aiter__(self):
        return sync_to_async(self.resolve_generator)()

    @abc.abstractmethod
    def resolve_generator(self) -> U:
        return NotImplemented


class URLQueryGenerator(BaseURLGenerator[URL]):
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

    def __init__(
        self,
        url: URL,
        *,
        param: Optional[str] = None,
        initial_value: int = 0,
        end_value: int = 0,
        step: int = 1,
        param_type: str = "number",
        query: dict[str, str | int] = {},
    ):
        acceptable_types = ["number", "letter"]

        if param_type not in acceptable_types:
            raise ValueError("Valid parameter types are: number, letter")

        self.url_instance = URL(url)
        self.parameter_type = param_type
        self.query = self.check_initial_query(query)

        self.initial_value = initial_value
        self.end_value = end_value
        self.step = step
        self.param = param

    def __len__(self) -> int:
        return len(list(self.resolve_generator()))

    @staticmethod
    def check_initial_query(query: dict[str, str | int]):
        """Function that checks if a value of the
        query dict is None and replaces it with an
        empty string"""
        clean_query: dict[str, str | int] = {}
        for key, value in query.items():
            if value is None:
                clean_query[key] = ""
                continue
            clean_query[key] = value
        return clean_query

    @override
    def resolve_generator(self):
        if self.parameter_type == "number":
            calculated_range = 0
            if self.initial_value < 0 or self.end_value < 0:
                raise ValueError("End value cannot be below initial value")

            calculated_range = self.end_value - self.initial_value
            for i in range(calculated_range):
                if (i % self.step) == 0:
                    value = self.initial_value + i

                    full_query = self.query | {self.param: value}
                    query = urlencode(full_query)

                    yield URL(str(self.url_instance) + f"?{query}")

        if self.parameter_type == "letter":
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
        return f"<{self.__class__.__name__}: {self.__len__()}>"

    def __len__(self):
        return len(list(self.resolve_generator()))

    def resolve_generator(self):
        new_params = []
        base_params = [self.params for _ in range(self.k)]
        for i, param in enumerate(base_params, start=self.start):
            new_param = {}
            for key, value in param.items():
                if value == "number" or value == "k":
                    new_param[key.removeprefix("$")] = i
            new_params.append(new_param)

        for i in range(self.k):
            try:
                yield self.base_template_url.substitute(new_params[i])
            except KeyError:
                yield self.base_template_url


class URLPaginationGenerator(BaseURLGenerator[URL]):
    """This class generates a set of URLs by adding a pagination query parameter
    to a base URL. This is useful for creating URLs that correspond to different
    pages of a paginated website.

    It takes a base URL and a pagination query parameter name, and generates a
    set of URLs with the pagination parameter incremented sequentially. This allows for the
    creation of multiple URLs to explore different pages of a paginated website.

    >>> PagePaginationGenerator('http:////example.com', k=2)
    ... ['http:////example.com?page=1', 'http:////example.com?page=2']
    """

    def __init__(self, url: TypeUrl, param_name: str = "page", k: int = 10):
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
        return f"<{self.__class__.__name__}: {len(self.final_urls)}>"

    def __len__(self):
        return len(self.final_urls)

    def resolve_generator(self):
        url = str(self.url)

        for _ in range(self.k):
            self.urls.append(url)

        counter = 1
        for url in self.urls:
            final_query = urlencode({self.param_name: str(counter)}, encoding="utf-8")
            yield url + f"?{final_query}"
            counter = counter + 1
