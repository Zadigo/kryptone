import csv
import dataclasses
import json
import pathlib
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Optional

import gspread
import pyairtable
import redis
from internal_types import FileProtocol, _SiteCrawler

from kryptone import logger
from kryptone.conf import settings
from kryptone.utils.encoders import DefaultJsonEncoder
from kryptone.utils.text import color_text
from kryptone.utils.urls import URL, load_image_extensions

if TYPE_CHECKING:
    from kryptone.base import SiteCrawler


def simple_list_adapter(data: list[Any]) -> list[list[Any]]:
    """This is useful in cases where we send
    a simple list [1, 2] which needs to be
    adapted to a csv array [[1], [2]]
    """
    return list(map(lambda x: [x], data))


class BaseStorage:
    """Storage backends are primarily used for storing the
    current state of the spider either to a local source
    (such as a file) or external sources such as a database
    (e.g. Redis, PostGres) or HTTP endpoints. Their primary
    role is to also resume the previous known state of the
    spider if it has happened for it to be stopped and
    relaunched to its previous known point

    All storages must extend from this base storage class and
    therefore implement three base functions: `save`, `save_or_create`,
    `has` and `get`. They must return a coroutine.
    """

    storage_class = None
    storage_connection = None
    file_based = False
    connection_error = (
        'Failed connection to {storage_name}. The spider will '
        'keep running without a storage backend. Data might be lost!'
    )

    def __init__(self, spider: Optional[_SiteCrawler] = None):
        self.spider = spider
        self.is_connected = False
        self.spider_uuid: Optional[str] = None

        if self.spider is not None:
            self.spider_uuid = str(getattr(self.spider, 'spider_uuid'))

    def before_save(self, data: Any):
        """A hook that is execute before data
        is saved to the storage"""
        return data

    def initialize(self):
        """A hook function that used to
        preload data (for example files) in the
        storage container"""
        return NotImplemented

    async def has(self, key: str) -> bool:
        return NotImplemented

    async def get(self, key: str) -> Any:
        return NotImplemented

    async def save(self, key: str, data: Any, adapt_list: bool = False, **kwargs) -> Any:
        return NotImplemented

    async def save_or_create(self, key: str, data: Any, **kwargs) -> Any:
        """Alternate save function that can be used to either
        save existing data or create a new record if the element
        does not exist. The logic needs to be implemented by the
        subclasses since the default behaviour is to call `save`"""
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

    def __init__(self, *, spider: Optional[_SiteCrawler] = None, storage_path: Optional[pathlib.Path | str] = None, ignore_images: bool = True):
        super().__init__(spider=spider)
        if storage_path is not None:
            if isinstance(storage_path, str):
                storage_path = pathlib.Path(storage_path)

            if not storage_path.is_dir():
                raise ValueError(
                    f"Storage should be a folder. Got: {storage_path}")

        self.storage = OrderedDict()
        self.storage_path = storage_path or settings.MEDIA_PATH
        self.ignore_images = ignore_images
        # Since it's a file, the connection to the
        # local file is always considered to be True
        self.is_connected = True
        self.initialize()

    def __repr__(self):
        return f'<{self.__class__.__name__}: {len(self.storage.keys())}>'

    def initialize(self):
        """A hook function that used to
        preload data (for example files) in the
        storage container. This hook should be
        called also when creating new files in
        the storage in order to keep track"""
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

    async def has(self, key: str) -> bool:
        return key in self.storage

    async def get(self, filename: str):
        """Reads the file and returns its content"""
        file = await self.get_file(filename)
        return await file.read()

    async def get_file(self, filename: str) -> FileProtocol:
        """Return a file from the storage. The extension
        of the filename should be specified"""
        # TODO: Instead of raising a dry error if the
        # file does not exist, create the file, reload
        # the storage and return the newly created item -;
        # we can also create the file in memory
        return self.storage[filename]

    async def save_or_create(self, filename: str, data: Any, **kwargs):
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
                    writer.writerows(data)
            self.initialize()
            return True
        return await self.save(filename, data, **kwargs)

    async def save(self, filename: str, data: Any, adapt_list: bool = False):
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
    """A storage backend that implements basic storage
    functionnalities in addition of more advanced features
    in order to run complexe spider operations on Redis"""

    storage_class = redis.Redis

    def __init__(self, *, spider=None):
        super().__init__(spider=spider)
        self.storage_connection = self.storage_class(
            host=settings.STORAGE_REDIS_HOST,
            port=settings.STORAGE_REDIS_PORT,
            username=getattr(settings, 'STORAGE_REDIS_USERNAME'),
            password=getattr(settings, 'STORAGE_REDIS_PASSWORD')
        )
        self.initialize()

    def initialize(self):
        try:
            self.storage_connection.ping()
        except:
            message = self.connection_error.format(
                storage_name=self.__class__.__name__)
            logger.critical(color_text('red', message))
        else:
            self.is_connected = True

    def before_save(self, data: Any) -> str:
        if isinstance(data, URL):
            data = str(data)

        if isinstance(data, (set, tuple)):
            data = list(data)

        if isinstance(data, (list, dict)):
            data = json.dumps(data, cls=DefaultJsonEncoder)

        return str(data)

    async def has(self, key: str) -> bool:
        value = self.storage_connection.get(key)
        return False if value is None else True

    async def update_iteration(self, by: int = 1):
        self.storage_connection.incrby('iteration', by)

    async def save(self, key: str, data: Any):
        data = self.before_save(data)

        if self.spider_uuid is None:
            return None

        return self.storage_connection.hset(self.spider_uuid, key, data)

    async def save_or_create(self, key, data, **kwargs):
        # Based on the type of data that we get in the
        # backend, we should ensure that the saving function
        # matches the type of data that we are passing
        if key == f'{settings.CACHE_FILE_NAME}.json':
            for key, value in data.items():
                await self.save(key, value)
        elif key == 'seen_urls.csv':
            await self.save('seen_urls.csv', data)
        else:
            await self.save(key, data)

    async def get(self, key: str):
        if self.spider_uuid is not None:
            result = self.storage_connection.hget(self.spider_uuid, key)

            if result is not None and isinstance(result, bytes):
                data = result.decode()

                try:
                    # If the item is a list or dict,
                    # this will attempt to return it
                    return json.loads(data)
                except:
                    pass

                try:
                    # If the item is an integer,
                    # return it as such
                    return int(data)
                except:
                    pass

                return data
        return None


class AirtableStorage(BaseStorage):
    storage_class = pyairtable.Api

    def __init__(self):
        super().__init__()
        self.storage_connection = self.storage_class(
            settings.STORAGE_AIRTABLE_API_KEY)


# class ApiStorage(BaseStorage):
#     """A storage that uses GET/POST requests in order
#     to save data that was processed by the Spider to
#     HTTP endpoints"""

#     def __init__(self, *, spider=None):
#         super().__init__(spider=spider)
#         self.session = requests.Session()
#         self.get_endpoint = getattr(settings, 'STORAGE_API_GET_ENDPOINT')
#         self.save_endpoint = getattr(settings, 'STORAGE_API_SAVE_ENDPOINT')

#     @property
#     def default_headers(self):
#         return {
#             'Content-Type': 'application/json'
#         }

#     async def check(self, key, data):
#         """Checks that the data that is returned is formatted
#         to be understood and used by the spider. This is
#         only for system type data like the cache"""
#         names = ['cache']

#         if key not in names:
#             return False

#         if not isinstance(data, dict):
#             raise TypeError('Data should be a dictionnary')

#         keys = data.keys()

#         if key == 'cache':
#             required_keys = [
#                 'spider', 'spider_uuid',
#                 'timestamp', 'urls_to_visit',
#                 'visited_urls'
#             ]
#             if list(keys) != required_keys:
#                 return False
#         return True

#     def create_request(self, url, method='post', data=None):
#         if method == 'post':
#             params = {'json': data}
#         else:
#             params = {'data': data}

#         request = requests.Request(
#             method=method,
#             url=url,
#             headers=self.default_headers,
#             **params
#         )
#         return self.session.prepare_request(request)

#     async def has(self, key):
#         # Assume the user ensures that the key that
#         # he is trying to get exists on the enpoint
#         return True

#     async def get(self, key):
#         """Endpoint that gets data by name on the
#         given endpoint. For example returning the
#         cache or the seen_urls"""
#         query = urlencode({
#             'q': key,
#             'id': self.spider_uuid
#         })

#         url = self.get_endpoint + f'?{query}'
#         request = self.create_request(url, method='get')

#         try:
#             response = self.session.send(request)
#         except requests.ConnectionError:
#             raise
#         except Exception:
#             raise
#         else:
#             if response.status_code == 200:
#                 state = await self.check(key, response.json())
#                 return response.json()
#             raise requests.ConnectionError("Could not save data to endpoint")

#     async def save(self, key, data, **kwargs):
#         """Endpoint that creates new data to the
#         given endpoint. The endpoint sends the results
#         under a given key which allows the endpoint to
#         dispatch the data correctly on its backend. This
#         process is important because it allows us thereafter
#         to retrieve the given data with the given key once
#         the user implements the logic to return it correctly"""
#         data = self.before_save(data)

#         template = {
#             'q': key,
#             'id': self.spider_uuid,
#             'items': data
#         }
#         request = self.create_request(self.save_endpoint, data=template)

#         try:
#             response = self.session.send(request)
#         except requests.ConnectionError:
#             raise
#         except Exception as e:
#             raise
#         else:
#             if response.status_code == 200:
#                 return response.json()
#             raise requests.ConnectionError("Could not save data to endpoint")


# class MemCacheSerializer:
#     def serialize(self, key, value):
#         if isinstance(value, str):
#             return (value.encode('utf-8'), 1)
#         return (json.dumps(value).encode('utf-8'), 2)

#     def deserialize(self, key, value, flags):
#         if flags == 1:
#             return value.decode('utf-8')
#         if flags == 2:
#             return json.loads(value.decode('utf-8'), cls=DefaultJsonEncoder)
#         raise Exception("Unknown serialization format")


# class MemCacheStorage(BaseStorage):
#     storage_class = pymemcache.Client

#     def __init__(self):
#         super().__init__()

#         default_params = {
#             'connect_timeout': 30,
#             'timeout': 60,
#             'no_delay': True
#         }

#         if settings.STORAGE_MEMCACHE_LOAD_BALANCER:
#             self.storage_connection = pymemcache.HashClient(
#                 settings.STORAGE_MEMCACHE_LOAD_BALANCER,
#                 **default_params
#             )
#         else:
#             self.storage_connection = self.storage_class(
#                 (
#                     settings.STORAGE_MEMCACHE_HOST,
#                     settings.STORAGE_MEMCACHE_PORT,
#                 ),
#                 **default_params
#             )


# class PostGresStorage(BaseStorage):
#     TRANSACTION = 'begin; {sql} commit'

#     CREATE_TABLE = 'create table if not exists {table} ({columns})'

#     SELECT = 'select {columns} from {table}'
#     WHERE_CONDITION = 'where {condition}'

#     INSERT = 'insert into {table} ({columns}) values ({values})'

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.initialize()
#         self.schema = 'spider'

#     def __quit__(self):
#         if self.is_connected:
#             self.storage_connection.close()

#     @staticmethod
#     def comma_join(fields):
#         return ', '.join(fields)

#     @staticmethod
#     def quote_value(value):
#         if isinstance(value, (int, float)):
#             return value

#         if isinstance(value, bool):
#             return 1 if value else 0

#         value = str(value)

#         if value.startswith("'"):
#             return value
#         return f"'{value}'"

#     @staticmethod
#     def finalize(value):
#         if value.endswith(';'):
#             return value
#         return f"{value};"

#     def quote_values(self, *values):
#         for value in values:
#             yield self.quote_value(value)

#     def build_condition(self, **params):
#         column = params.get('column')
#         condition_value = params.get('condition', '=')
#         quoted_value = self.quote_value(params.get('value'))
#         return f"{column}{condition_value}{quoted_value}"

#     def join_tokens(self, *tokens, separator=' ', finalize_each=False):
#         if finalize_each:
#             return separator.join(self.finalize(x) for x in tokens)
#         return separator.join(tokens)

#     def get_cursor(self):
#         if self.is_connected:
#             return self.storage_connection.cursor()
#         return None

#     def run_cursor(self, sql):
#         """Get a cursor and execute an initial
#         sql statement returns both the result and
#         the cursor for more operations"""
#         cursor = self.get_cursor()
#         if cursor is not None:
#             try:
#                 sql = self.finalize(sql)
#                 result = cursor.execute(sql)
#             except Exception as e:
#                 print(e)
#             else:
#                 return result, cursor

#     def initialize(self):
#         import psycopg

#         try:
#             template = 'dbname={db} user={user} password={password} host={host} port={port}'
#             conn_information = template.format(**{
#                 'db': settings.STORAGE_POSTGRESQL_DB_NAME,
#                 'user': settings.STORAGE_POSTGRESQL_USER,
#                 'password': settings.STORAGE_POSTGRESQL_PASSWORD,
#                 'host': settings.STORAGE_POSTGRESQL_HOST,
#                 'port': settings.STORAGE_POSTGRESQL_PORT,
#             })
#             self.storage_connection = connection = psycopg.connect(
#                 conninfo=conn_information
#             )
#         except Exception as e:
#             message = self.connection_error.format(
#                 storage_name=self.__class__.__name__)
#             logger.critical(color_text('red', message))
#             logger.critical(str(e))
#             return
#         else:
#             self.is_connected = True

#         sql = 'create schema if not exists spider'
#         result, cursor = self.run_cursor(sql)

#         # Tables
#         table1 = self.CREATE_TABLE.format(**{
#             'table': 'spider.seen_urls',
#             'columns': self.comma_join(
#                 [
#                     'id bigserial primary key',
#                     "url varchar(1500) unique not null check(url <> '')",
#                     'created_on timestamp'
#                 ]
#             )
#         })

#         table2 = self.CREATE_TABLE.format(**{
#             'table': 'spider.url_cache',
#             'columns': self.comma_join(
#                 [
#                     'id bigserial primary key',
#                     "url varchar(1500) unique not null check(url <> '')",
#                     'visited boolean default false',
#                     'created_on timestamp'
#                 ]
#             )
#         })

#         transaction = self.TRANSACTION.format(**{
#             'sql': self.join_tokens(table1, table2, finalize_each=True)
#         })

#         cursor.execute(transaction)
#         connection.commit()
#         cursor.close()

#     def select_sql(self, table: str):
#         return self.SELECT.format_map(**{'table': table})

#     def insert_sql(self, table: str, *values: str | URL):
#         d = str(datetime.datetime.now().date())
#         data = [(str(value), False, d) for value in values]

#         with self.get_cursor() as c:
#             sql = self.INSERT.format(**{
#                 'table': f'{self.schema}.{table}',
#                 'columns': self.join_tokens('url', 'visited', 'created_on', separator=', '),
#                 'values': '%s, %s, %s'
#             })
#             on_conlict_sql = f'{sql} on conflict (url) do nothing'
#             c.executemany(on_conlict_sql, data)
#             self.storage_connection.commit()

#     async def save(self, key, data, adapt_list=False, **kwargs):
#         if key == f'{settings.CACHE_FILE_NAME}.json':
#             urls_to_visit = data['urls_to_visit']
#             visited_urls = data['visited_urls']
#             self.insert_sql('url_cache', urls_to_visit)
#         elif key == 'seen_urls.csv':
#             self.insert_sql('url_cache', data)

    # def create_sql(self, table, column, value):
    #     return

    # def insert_sql(self, table, columns=[], values=[]):
    #     columns = self.comma_join(columns)
    #     values = self.comma_join(self.quote_values(*values))
    #     return self.INSERT.format(table=table, columns=columns, values=values)

    # def run_sql_statements(self, *tokens):
    #     sql = self.join_tokens(*tokens)
    #     cursor = self.storage_connection.cursor()
    #     return cursor.execute(self.finalize(sql))

    # def save(self, key, data, adapt_list=False, **kwargs):
    #     return

    # def visited_urls(self, state=True):
    #     select_sql = self.select_sql('url_cache')
    #     condition = self.build_condition(visited=state)
    #     where_condition = self.WHERE_CONDITION.format(condition=condition)
    #     return self.run_sql_statements(select_sql, where_condition)


class GoogleSheetStorage(BaseStorage):
    storage_class = None

    def __init__(self, spider=None):
        super().__init__(spider=spider)

        path = pathlib.Path(settings.STORAGE_GOOGLE_SHEET_CREDENTIALS)
        with open(path, mode='r', encoding='utf-8') as f:
            credentials = json.load(f)
            self.storage_connection = gspread.service_account_from_dict(
                credentials)
            self.spreadsheet = self.storage_connection.open_by_key(
                settings.STORAGE_GOOGLE_SHEET_ID
            )
