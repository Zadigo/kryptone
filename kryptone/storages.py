import csv
import dataclasses
import json
import pathlib
from collections import OrderedDict

import pyairtable
import pymemcache
import redis
import requests

from kryptone.conf import settings
from kryptone.utils.encoders import DefaultJsonEncoder
from kryptone.utils.urls import load_image_extensions


def simple_list_adapter(data):
    """This is useful in cases where we send
    a simple list [1, 2] which needs to be
    adapted to a csv array [[1], [2]]
    """
    return list(map(lambda x: [x], data))


class BaseStorage:
    storage_class = None
    storage_connection = None
    file_based = False

    def __init__(self):
        self.spider = None

    def __get__(self, instance, cls=None):
        self.spider = instance
        return self

    def before_save(self, data):
        """A hook that is execute before data
        is saved to the storage"""
        return data

    def initialize(self):
        """A hook function that can be used to
        preload data (for example files) in the
        storage container. This hook should be
        called also when creating new files in
        the storage in order to keep track"""
        return NotImplemented

    async def has(self, key):
        return NotImplemented

    async def get(self, key):
        return NotImplemented

    async def save(self, key, data, adapt_list=False, **kwargs):
        return NotImplemented

    async def save_or_create(self, key, data, **kwargs):
        return self.save(key, data, **kwargs)


@dataclasses.dataclass
class File:
    path: pathlib.Path

    def __eq__(self, value):
        if dataclasses.is_dataclass(value):
            if isinstance(value, File):
                return (
                    value.path == self.path,
                    value.path.name == self.path.name
                )
        return value == self.path.name

    @property
    def is_json(self):
        return self.path.suffix == '.json'

    @property
    def is_csv(self):
        return self.path.suffix == '.csv'

    @property
    def is_image(self):
        return self.path.suffix in load_image_extensions()

    async def read(self):
        with open(self.path, mode='r', encoding='utf-8') as f:
            if self.is_json:
                return json.load(f)
            elif self.is_csv:
                reader = csv.reader(f)
                return list(reader)


class FileStorage(BaseStorage):
    """This file based storage api is used to write
    to files in the selected user storage"""

    file_based = True

    def __init__(self, storage_path=None, ignore_images=True):
        super().__init__()
        if storage_path is not None:
            if isinstance(storage_path, str):
                storage_path = pathlib.Path(storage_path)

        if not storage_path.is_dir():
            raise ValueError("Storage should be a folder")

        self.storage = OrderedDict()
        self.storage_path = storage_path or settings.MEDIA_PATH
        self.ignore_images = ignore_images
        self.initialize()

    def __repr__(self):
        return f'<{self.__class__.__name__}: {len(self.storage.keys())}>'

    def initialize(self):
        items = self.storage_path.glob('**/*')
        for item in items:
            if not item.is_file():
                continue
            instance = File(item)

            if self.ignore_images:
                if instance.is_image:
                    continue

            self.storage[item.name] = instance
        return True

    async def has(self, key):
        return key in self.storage

    async def get(self, filename):
        file = self.get_file(filename)
        return file.read()

    async def get_file(self, filename):
        return self.storage[filename]

    async def save_or_create(self, filename, data, **kwargs):
        file_exists = await self.has(filename)
        if not file_exists:
            path = self.storage_path.joinpath(filename)
            instance = File(path)

            if instance.is_json:
                with open(path, mode='w', encoding='utf-8') as f:
                    json.dump(data, f, cls=DefaultJsonEncoder)
            elif instance.is_csv:
                with open(path, mode='w', newline='\n', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(data)
            self.initialize()
            return True
        return await self.save(filename, data, **kwargs)

    async def save(self, filename, data, adapt_list=False):
        data = self.before_save(data)
        file = await self.get_file(filename)

        if file.is_json:
            with open(file.path, mode='w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, cls=DefaultJsonEncoder)
        elif file.is_csv:
            with open(file.path, mode='w', newline='\n', encoding='utf-8') as f:
                writer = csv.writer(f)

                if adapt_list:
                    data = simple_list_adapter(data)
                writer.writerows(data)
        return True


class RedisStorage(BaseStorage):
    storage_class = redis.Redis

    def __init__(self):
        super().__init__()
        self.storage_connection = self.storage_class(
            settings.STORAGE_REDIS_HOST,
            settings.STORAGE_REDIS_PORT,
            username=getattr(settings, 'STORAGE_REDIS_USERNAME'),
            password=getattr(settings, 'STORAGE_REDIS_PASSWORD')
        )
        self.is_connected = False

    def initialize(self):
        try:
            self.storage_connection.ping()
        except:
            return False
        self.is_connected = True
        return self.is_connected


class AirtableStorag(BaseStorage):
    storage_class = pyairtable.Api

    def __init__(self):
        super().__init__()
        self.storage_connection = self.storage_class(
            settings.STORAGE_AIRTABLE_API_KEY)


class ApiStorage(BaseStorage):
    """A storage that uses GET/POST requests in order
    to save data that was processed by the Spider"""

    def __init__(self):
        self.session = requests.Session()
        self.get_endpoint = getattr(settings, 'STORAGE_API_GET_ENDPOINT')
        self.save_endpoint = getattr(settings, 'STORAGE_API_SAVE_ENDPOINT')

    @property
    def default_headers(self):
        return {
            'Content-Type': 'application/json'
        }

    async def check(self, key, data):
        """Checks that the data is returned is formatted
        to be understood and used by the spider. This is
        only for system type data"""
        names = ['cache']

        if key not in names:
            return False

        if not isinstance(data, dict):
            raise TypeError('Data should be a dictionnary')

        keys = data.keys()

        if key == 'cache':
            required_keys = [
                'spider', 'timestamp',
                'urls_to_visit', 'visited_urls'
            ]
            if list(keys) != required_keys:
                return False
        return True

    def create_request(self, url, method='post', data=None):
        request = requests.Request(
            method=method,
            url=url,
            headers=self.default_headers,
            data=data
        )
        return self.session.prepare_request(request)

    async def get(self, key):
        """Endpoint that gets data by name on the
        given endpoint"""
        url = self.get_endpoint + f'?data={key}'
        request = self.create_request(url, method='get')

        try:
            response = self.session.send(request)
        except requests.ConnectionError:
            raise
        except Exception:
            raise
        else:
            if response.status_code == 200:
                return self.check(key, response.json())
            raise requests.ConnectionError("Could not save data to endpoint")

    async def save(self, key, data, **kwargs):
        """Endpoint that creates new data to the
        given endpoint. The endpoint sends the results
        under a given key which allows the endpoint to
        dispatch the data correctly on its backend. This
        process is important because it allows us thereafter
        to retrieve the given data with the given key once
        the user implements the logic to return it correctly"""
        data = self.before_save(data)

        template = {
            'data_name': key,
            'results': data
        }
        request = self.create_request(self.save_endpoint, data=template)

        try:
            resposne = self.session.send(request)
        except requests.ConnectionError:
            raise
        except Exception:
            raise
        else:
            if resposne.status_code == 200:
                return True
            raise requests.ConnectionError("Could not save data to endpoint")


class MemCacheSerializer:
    def serialize(self, key, value):
        if isinstance(value, str):
            return (value.encode('utf-8'), 1)
        return (json.dumps(value).encode('utf-8'), 2)

    def deserialize(self, key, value, flags):
        if flags == 1:
            return value.decode('utf-8')
        if flags == 2:
            return json.loads(value.decode('utf-8'), cls=DefaultJsonEncoder)
        raise Exception("Unknown serialization format")


class MemCacheStorage(BaseStorage):
    storage_class = pymemcache.Client

    def __init__(self):
        super().__init__()

        default_params = {
            'connect_timeout': 30,
            'timeout': 60,
            'no_delay': True
        }

        if settings.STORAGE_MEMCACHE_LOAD_BALANCER:
            self.storage_connection = pymemcache.HashClient(
                settings.STORAGE_MEMCACHE_LOAD_BALANCER,
                **default_params
            )
        else:
            self.storage_connection = self.storage_class(
                (
                    settings.STORAGE_MEMCACHE_HOST,
                    settings.STORAGE_MEMCACHE_PORT,
                ),
                **default_params
            )
