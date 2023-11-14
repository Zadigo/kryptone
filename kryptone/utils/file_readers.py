import csv
import itertools
import json
from functools import cached_property, lru_cache

from kryptone import logger
from kryptone.conf import settings
from kryptone.utils.encoders import DefaultJsonEncoder


def tokenize(func):
    @lru_cache(maxsize=100)
    def reader(filename, *, as_list=False):
        data = func(filename)
        return data.split('\n') if as_list else data
    return reader


def get_media_folder(filename):
    if settings.PROJECT_PATH is not None:
        return settings.PROJECT_PATH.joinpath('media', filename)
    return filename


@tokenize
def read_document(filename):
    """Reads a document of some sort"""
    path = get_media_folder(filename)
    with open(path, mode='r', encoding='utf-8') as f:
        data = f.read()
    return data


def read_documents(*filenames):
    """Reads and combines multiple documents at once"""
    items = []
    for filename in filenames:
        data = read_document(filename, as_list=True)
        items.extend(data)
    return items
    # text = []
    # for item in items:
    #     data = item.read()
    #     text.extend(data.decode().split('\r\n'))
    #     item.close()
    # return text


def read_json_document(filename):
    path = get_media_folder(filename)
    with open(path, mode='r', encoding='utf-8') as f:
        data = json.load(f)
        return data


def write_json_document(filename, data):
    """Writes data to a JSON file"""
    path = get_media_folder(filename)
    with open(path, mode='w+', encoding='utf-8') as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False,
            cls=DefaultJsonEncoder
        )


def read_csv_document(filename, flatten=False):
    """Reads and returns the data of a csv document"""
    path = get_media_folder(filename)
    with open(path, mode='r', encoding='utf-8') as f:
        data = list(csv.reader(f))
        if flatten:
            return list(itertools.chain(*data))
        return data


def write_csv_document(filename, data, adapt_data=False):
    """Writes data to a CSV file

    >>> write_csv_document('example.csv', [[1], [2]])

    If you send in a simple array [1, 2], use `adapt_data`
    to transform it into a csv usable array 
    """
    path = get_media_folder(filename)
    with open(path, mode='w', newline='\n', encoding='utf-8') as f:
        writer = csv.writer(f)

        if isinstance(data, set):
            data = list(data)

        if not isinstance(data, list):
            data = [data]

        if adapt_data:
            # This is useful in cases where we send
            # a simple list [1, 2] which needs to be
            # adapted to a csv array [[1], [2]]
            data = list(map(lambda x: [x], data))

        writer.writerows(data)


def write_text_document(filename, data, encoding='utf-8'):
    """Writes text to a txt file

    >>> write_csv_document('example.txt', 'some text')
    """
    path = get_media_folder(filename)
    with open(path, mode='w', encoding=encoding) as f:
        f.write(data)


class LoadJS:
    def __init__(self, filename):
        self.filename = filename
        self._project_path = settings.PROJECT_PATH
        self.files = []
        if self._project_path is not None:
            self.files = list(
                self._project_path.joinpath('js').glob('**/*.js'))

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.filename}">'

    @cached_property
    def content(self):
        file = list(filter(lambda x: x.name == self.filename, self.files))
        if file:
            with open(file[-1], mode='r') as f:
                data = f.read()
                return data
        logger.warning('No JS file named {self.filename} found in the project')
        return ''


class LoadStartUrls:
    """Loads the start urls from a csv file.
    The filename should be provided without
    the file extension"""

    def __init__(self, filename='start_urls', is_json=False):
        self.is_json = is_json
        extension = 'json' if self.is_json else 'csv'
        self.filename = f'{filename}.{extension}'

    def __iter__(self):
        for url in self.content:
            yield url

    @cached_property
    def content(self):
        if self.is_json:
            with open(settings.PROJECT_PATH / self.filename, mode='r', encoding='utf-8') as f:
                data = json.load(f)
                return list(set(item['url'] for item in data))
        else:
            with open(settings.PROJECT_PATH / self.filename, mode='r', encoding='utf-8') as f:
                data = set(list(itertools.chain(*csv.reader(f))))
                return data
