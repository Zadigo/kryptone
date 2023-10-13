import itertools
import re
from collections import defaultdict
from functools import cached_property
from urllib.parse import urlparse
from collections import defaultdict
import datetime
import re
from collections import OrderedDict
from urllib.parse import urlparse

import pytz

from string import Template
from collections import defaultdict
import re
from urllib.parse import urlparse

def drop_null(items, remove_empty_strings=True):
    for item in items:
        if remove_empty_strings and item == '':
            continue

        if item is not None:
            yield item


def keep_while(predicate, items):
    for item in items:
        if not predicate(item):
            continue
        yield item


def drop_while(predicate, items):
    for item in items:
        if predicate(item):
            continue
        yield item


def group_by(predicate, items):
    lhvs = []
    rhvs = []
    for item in items:
        if predicate(item):
            lhvs.append(item)
        else:
            rhvs.append(item)
    return lhvs, rhvs


def iterate_chunks(items, n):
    """Function that creates and iterates over
    chunks of data
    
    >>> iterate_chunks([1, 2, 3], 2)
    ... [1, 2]
    ... [3]
    """
    if n < 1:
        raise ValueError(f'n must be greater or equal to 1. Got: {n}')

    it = iter(items)
    while True:
        chunked_items = itertools.islice(it, n)
        try:
            first_element = next(chunked_items)
        except StopIteration:
            return
        yield itertools.chain((first_element,), chunked_items)


class CombinedIterators:
    def __init__(self, *iterators):
        self.iterators = list(iterators)

    def __repr__(self):
        class_name = self.__class__.__name__
        return f'<{class_name} {self.iterators}>'

    def __iter__(self):
        for url in self.urls:
            yield url[0]

    def __add__(self, obj):
        # Add the new iterator to the
        # list of iterators
        self.iterators.append(obj)
        return self

    @cached_property
    def urls(self):
        urls_list = []
        for item in self.iterators:
            urls = list(item)
            for url in urls:
                urls_list.append(url[1])
        return urls_list

    @cached_property
    def classified_images(self):
        return_result = []
        for item in self.iterators:
            return_result.append(item.classified_images)
        return return_result

    @cached_property
    def as_dict(self):
        return_result = {}
        for item in self.iterators:
            return_result.update(item.as_dict)
        return return_result

    @cached_property
    def as_csv(self):
        items = []
        for item in self.iterators:
            urls = list(item)
            for alt, url in urls:
                items.append([item.page_url, alt, url])
        return items


class PageImagesIterator:
    """An iterator for storing images collected
    on a given page. This will by default get any
    images on the page except base64 types

    Subclass PageImagesIterator to collect specific
    types of images.
    """

    images_list_filter = []

    def __init__(self, current_url, image_elements):
        self.urls = []
        self.page_url = current_url
        self._cached_images = []
        self.extensions = set()

        extension_regex = re.compile(r'\.(\w+)$')

        for image in image_elements:
            image_alt = image.get_attribute('alt')
            src = image.get_attribute('src')

            if src is not None:
                url_object = urlparse(src)
                is_image = extension_regex.search(url_object.path)
                if is_image:
                    if is_image.group(1) not in self.images_list_filter:
                        continue
                    self.extensions.add(is_image.group(1))

                # We are not interested in base64 images
                if src.startswith('data:image'):
                    continue
                self.urls.append([image_alt, src])

    def __repr__(self):
        return f'<PageImages: {self.page_url}, {len(self.urls)} images>'

    def __iter__(self):
        for url in self.urls:
            yield url[0]

    def __len__(self):
        return len(self.urls)

    def __add__(self, obj):
        return CombinedIterators(self, obj)

    @cached_property
    def urls(self):
        items = []
        for url in self.urls:
            items.append(url[1])
        return items

    @cached_property
    def classified_images(self):
        classified_images_container = defaultdict(set)
        for extension in self.extensions:
            container = classified_images_container[extension]
            for url in self.urls:
                container.add(url[1])
        return classified_images_container

    @cached_property
    def as_dict(self):
        """Returns each collected under a dict format
        useful for saving the data in a JSON file"""
        def normalize_data(values):
            name = values[0]
            name = None if name == '' else name
            return {
                'name': name,
                'url': values[1]
            }
        return {self.page_url: list(map(normalize_data, self.urls))}

    @cached_property
    def as_csv(self):
        items = []
        for alt, url in self.urls:
            items.append([self.page_url, alt, url])
        return items


class JPEGImagesIterator(PageImagesIterator):
    """Will collect only jpg and jpeg images"""

    images_list_filter = ['jpg', 'jpeg']


class EcommercePageImagesIterator(JPEGImagesIterator):
    """Same as PageImagesIterator but applies an additional
    filter to classify images related by a specific
    collection together
    """


class AsyncIterator:
    def __init__(self, data, by=10):
        self.data = data
        self.by = by

    def __alen__(self):
        return len(self.data)

    def __aiter__(self):
        result = iterate_chunks(self.data, self.by)
        for item in result:
            yield list(item)


class URLIterator:
    _urls_to_visit = set()
    _visited_urls = set()
    _seen_urls = set()
    _grouped_by_page = defaultdict(set)
    _current_url = None

    def __init__(self, start_urls=[], sort_urls=False):
        self.sort_urls = sort_urls
        result = self.pre_save(start_urls)
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
        """Returns the amount of urls
        left to visit"""
        return len(self._urls_to_visit)

    def __getitem__(self, index):
        from kryptone.utils.urls import URL
        url = list(self._urls_to_visit)[index]
        return URL(url)

    @property
    def empty(self):
        return len(self._urls_to_visit) == 0

    @property
    def urls_to_visit(self):
        from kryptone.utils.urls import URL
        for url in self._urls_to_visit:
            yield URL(url)

    @property
    def visited_urls(self):
        from kryptone.utils.urls import URL
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

    def append(self, url):
        self._seen_urls.add(url)

        if url in self._urls_to_visit:
            return False

        if url in self._visited_urls:
            return False

        self._urls_to_visit.add(url)
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
        from kryptone.utils.urls import URL
        url = self._urls_to_visit.pop()
        self._current_url = URL(url)
        self._visited_urls.add(url)
        return self._current_url


class URLGenerator:
    """Generates a set of urls using a template

    >>> generator = URLGenerator('http://example.com/$id', params={'id': 'number'}, k=2)
    ... ['http://example.com/1', 'http://example.com/2']
    """

    def __init__(self, template, params={}, k=10, start=0):
        self.base_template_url = Template(template)

        new_params = []
        base_params = [params for _ in range(k)]
        for i, param in enumerate(base_params, start=start):
            new_param = {}
            for key, value in param.items():
                if value == 'number':
                    new_param[key] = i
            new_params.append(new_param)

        self.urls = []
        for i in range(k):
            try:
                self.urls.append(
                    self.base_template_url.substitute(new_params[i])
                )
            except KeyError:
                self.urls.append(template)

    def __iter__(self):
        for url in self.urls:
            yield url

    def __aiter__(self):
        for url in self.urls:
            yield url

    def __len__(self):
        return len(self.urls)



# class W:
#     def __init__(self, *values):
#         self.values = list(values)

#     def __iter__(self):
#         for value in self.values:
#             for x in value:
#                 yield x

#     def __add__(self, obj):
#         self.values.append(obj)
#         return self


# class S:
#     def __add__(self, obj):
#         return W(self, obj)


# class A(S):
#     def __iter__(self):
#         for i in range(5):
#             yield i


# class B(S):
#     def __iter__(self):
#         for i in range(5):
#             yield i


# class C(S):
#     def __iter__(self):
#         for i in [100, 200]:
#             yield i


# class D(S):
#     def __iter__(self):
#         for i in ['a']:
#             yield i


# w = A() + C() + B() + D()
# print(list(w))
