import csv
import itertools
import json
from functools import lru_cache
from typing import Callable

from kryptone.conf import settings
from kryptone.utils.encoders import DefaultJsonEncoder
from kryptone.utils.deprecation import deprecated


def tokenize(func: Callable[[str], str]):
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
def read_document(filename: str):
    """Reads a document of some sort"""
    path = get_media_folder(filename)
    with open(path, mode='r', encoding='utf-8') as f:
        data = f.read()
    return data


def read_documents(*filenames: str):
    """Reads and combines multiple documents at once"""
    items = []
    for filename in filenames:
        data = read_document(filename, as_list=True)
        items.extend(data)
    return items


@deprecated
def read_json_document(filename: str):
    path = get_media_folder(filename)
    with open(path, mode='r', encoding='utf-8') as f:
        data = json.load(f)
        return data


@deprecated
def write_json_document(filename: str, data: dict):
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


@deprecated
def read_csv_document(filename: str, flatten: bool = False):
    """Reads and returns the data of a csv document"""
    path = get_media_folder(filename)
    with open(path, mode='r', encoding='utf-8') as f:
        data = list(csv.reader(f))
        if flatten:
            return list(itertools.chain(*data))
        return data


@deprecated
def write_csv_document(filename: str, data: list, adapt_data: bool = False):
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


@deprecated
def write_text_document(filename: str, data: str, encoding: str = 'utf-8'):
    """Writes text to a txt file

    >>> write_csv_document('example.txt', 'some text')
    """
    path = get_media_folder(filename)
    with open(path, mode='w', encoding=encoding) as f:
        f.write(data)
