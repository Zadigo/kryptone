from collections import OrderedDict

from kryptone.utils.urls import URL


class Route:
    def __init__(self):
        self.path = None
        self.regex = None
        self.name = None
        self.function_name = None
        self.matched_urls = []

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
                result = current_url.url_object.path == path

            if regex is not None:
                result = current_url.test_path(regex)

            if result:
                func = getattr(spider_instance, function_name, False)
                if not func:
                    raise ValueError('The Router requires for you to '
                                     'have a matching function on your spider')
                func(current_url, route=self)
                if result:
                    self.matched_urls.append(current_url)
                return result
            return result
        return self, wrapper


route = Route()


class Router:
    """Call specific functions depending or whether the current
    visited url matches one of the routes.
    
    Let's say we have `http://example.com/product` and
    `http://example.com/products` and that we need to apply two
    different logics to these urls. That's where the Router comes
    in handy
    
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


# class Spider:
#     def get_product(self, current_url, **kwargs):
#         print(current_url, kwargs)


# spider = Spider()

# router = Router([
#     route('get_product', regex=r'\/google', name='product')
# ])
# # route = router.routes['product']
# # route('http://example.com/google', spider)
# print(router)
