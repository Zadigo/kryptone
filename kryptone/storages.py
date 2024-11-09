import csv
import dataclasses
import json
import pathlib
from collections import OrderedDict

import pyairtable
import redis
import requests
from io import BytesIO
from kryptone.conf import settings
from kryptone.utils.encoders import DefaultJsonEncoder


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
        self.storage_path = None
        self.spider = None

    def __get__(self, instance, cls=None):
        self.spider = instance
        return self

    def before_save(self, data):
        """A hook that is execute before data
        is saved to the storage"""
        return data

    def initialize(self):
        return NotImplemented


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

    def read(self):
        with open(self.path, mode='r', encoding='utf-8') as f:
            if self.is_json:
                return json.load(f)
            elif self.is_csv:
                reader = csv.reader(f)
                return list(reader)


class FileStorage(BaseStorage):
    file_based = True

    def __init__(self, storage_path=None):
        if storage_path is not None:
            if isinstance(storage_path, str):
                storage_path = pathlib.Path(storage_path)

        if not storage_path.is_dir():
            raise ValueError("Storage should be a folder")

        self.storage = OrderedDict()
        self.storage_path = storage_path or settings.MEDIA_PATH

    def __repr__(self):
        return f'<{self.__class__.__name__}: {len(self.storage.keys())}>'

    def initialize(self):
        items = self.storage_path.glob('**/*')
        for item in items:
            if not item.is_file():
                continue
            self.storage[item.name] = File(item)
        return True

    def has_file(self, filename):
        return filename in self.storage

    def get_file(self, filename):
        return self.storage[filename]

    def read_file(self, filename):
        file = self.get_file(filename)
        return file.read()
    
    def save_or_create(self, filename, data, **kwargs):
        if not self.has_file(filename):
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
        return self.save(filename, data, **kwargs)

    def save(self, filename, data, adapt_list=False):
        file = self.get_file(filename)
        data = self.before_save(data)

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

    def check(self, name, data):
        """Checks that the data is returned is formatted
        to be understood and used by the spider. This is
        only for system type data"""
        names = ['cache']

        if name not in names:
            return data

        if not isinstance(data, dict):
            raise TypeError('Data should be a dictionnary')

        keys = data.keys()

        if name == 'cache':
            required_keys = ['spider', 'timestamp',
                             'urls_to_visit', 'visited_urls']
            if list(keys) != required_keys:
                raise ValueError('Cache data is not valid')

    def create_request(self, url, method='post', data=None):

        request = requests.Request(
            method=method, url=url, headers=self.default_headers, data=data)
        return self.session.prepare_request(request)

    def get(self, data_name):
        """Endpoint that gets data by name on the
        given endpoint"""
        url = self.get_endpoint + f'?data={data_name}'
        request = self.create_request(url, method='get')

        try:
            response = self.session.send(request)
        except requests.ConnectionError:
            raise
        except Exception:
            raise
        else:
            if response.status_code == 200:
                return self.check(data_name, response.json())
            raise requests.ConnectionError("Could not save data to endpoint")

    def create(self, data_name, data):
        """Endpoint that creates new data to the
        given endpoint. The endpoint sends the results
        under a given key which allows the endpoint to
        dispatch the data correctly on its backend. This
        process is important because it allows us thereafter
        to retrieve the given data with the given key once
        the user implements the logic to return it correctly"""
        data = self.before_save(data)

        template = {
            'data_name': data_name,
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
