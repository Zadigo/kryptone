from collections import OrderedDict, deque

from kryptone import logger
from kryptone.utils.urls import URL


class Route:
    """Points to a specific function on the crawler for a 
    route that matches the specific path

    >>> router = Router([
    ...    route('logic_for_first_url', regex='\/products', name='products')
    ... ])
    """

    def __init__(self):
        self.path = None
        self.regex = None
        self.name = None
        self.function_name = None
        self.matched_urls = deque()

    def __repr__(self):
        return f'<Route <{self.path or self.regex}> name={self.name}>'

    def __call__(self, function_name, *, path=None, regex=None, name=None):
        self.name = name
        self.function_name = function_name
        self.path = path
        self.regex = regex

        def wrapper(current_url, spider_instance):
            if isinstance(current_url, str):
                current_url = URL(current_url)

            result = False
            if path is None and regex is None:
                raise ValueError('Both url path and regex cannot be None')

            if path is not None:
                # Make an exact match on the path ?
                result = current_url.url_object.path == path

            if regex is not None:
                result = current_url.test_path(regex)

            if result:
                func = getattr(spider_instance, function_name, False)
                if not func:
                    # Silently fail if we got no corresponding
                    # functions on the spider class
                    logger.warning(
                        f'Routing failed for: {current_url}. '
                        'No corresponding function found'
                    )
                    return False

                func(current_url, route=self)
                if result:
                    logger.info(
                        f"Routing sucessful for {current_url} "
                        f"to '{self.function_name}'"
                    )
                    self.matched_urls.appendleft(current_url)
                return result
            return result
        return self, wrapper

    @classmethod
    def new(cls):
        instance = cls()
        return instance


def route(function_name, *, path=None, regex=None, name=None):
    """Function that calls a new `Route` instance that uses
    extra functionnalities to better identify the route"""
    instance = Route.new()
    return instance(function_name, path=path, regex=regex, name=name)


class Router:
    """Manages a collection of routes and resolves URL matches by invoking 
    specific functions on a web crawler. The router enables the execution of 
    different logic for different URL patterns.

    >>> class MySpider:
    ...     start_url = 'http://example.com'
    ...     
    ...     class Meta:
    ...        router = Router([
    ...            route('logic_for_first_url', regex='\/products', name='products'),
    ...            route('logic_for_first_url', path='/product', name='product')
    ...        ])
    ...     
    ...     def logic_for_first_url(self, current_url, route=None, **kwargs):
    ...         pass
    ...         
    ...     def logic_for_second_url(self, current_url, route=None, **kwargs):
    ...         pass
    """

    routes = OrderedDict()

    def __init__(self, routes):
        for i, route in enumerate(routes):
            instance, wrapper = route
            if not callable(wrapper):
                raise
            if instance.name is not None:
                name = instance.name
            else:
                name = f'route_{i}'
            self.routes[name] = wrapper

    def __repr__(self):
        return f'<Router: {list(self.routes.keys())}>'

    @property
    def has_routes(self):
        return len(self.routes.keys()) > 0

    def resolve(self, current_url, spider_instance):
        """Resolves the given URL by matching it against the router's 
        routes and invoking the corresponding function on the spider 
        instance"""
        resolution_states = []
        for route in self.routes.values():
            state = route(current_url, spider_instance)
            resolution_states.append(state)
        return resolution_states
