import csv
import json
from functools import lru_cache, wraps
from io import FileIO

from kryptone import logger
from kryptone.conf import settings


def tokenize(func):
    @lru_cache(maxsize=100)
    def reader(filename, *, as_list=False):
        data = func(filename)
        return data.split('\n') if as_list else data
    return reader


def get_media_folder(filename):
    if settings.PROJECT_PATH is not None:
        return settings.PROJECT_PATH / filename
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
        json.dump(data, f, indent=4, ensure_ascii=False)


def write_csv_document(filename, data):
    """Writes data to a CSV file"""
    path = get_media_folder(filename)
    with open(path, mode='w', newline='\n', encoding='utf-8') as f:
        writer = csv.writer(f)

        if isinstance(data, set):
            data = list(data)

        if not isinstance(data, list):
            data = [data]

        writer.writerows(data)


class URLCache:
    def __init__(self):
        self.data = {}
        self._urls_to_visit = []
        self._visited_urls = []

    def __repr__(self) -> str:
        statistics = f'urls_to_visit={len(self._urls_to_visit)} '
        f'visited_urls={len(self._visited_urls)}'
        return f'<URLCache: {statistics}>'

    @property
    def urls_to_visit(self):
        return set(self._urls_to_visit)

    @property
    def visited_urls(self):
        return set(self._visited_urls)

    def load_from_file(self):
        data = read_json_document('cache.json')
        self._urls_to_visit = data['urls_to_visit']
        self._visited_urls = data['visited_urls']
        logger.info(f'Loaded {len(self._urls_to_visit)} urls')
        self.data = data

    def load_from_dict(self, data):
        if not isinstance(data, dict):
            raise ValueError('Data should be a dictionnary')
        self._urls_to_visit = data['urls_to_visit']
        self._visited_urls = data['visited_urls']
        self.data = data
