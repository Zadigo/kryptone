import re
from collections import defaultdict
from functools import cached_property
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

    @cached_property
    def as_dict(self):
        return_result = {}
        for item in self.iterators:
            return_result.update(item.as_dict)

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
