import os
from functools import cached_property

import airtable
import pymemcache
import redis
from dotenv import get_key

from kryptone import logger


class BaseConnection:
    """Base connection for all connections"""

    connection_class = None

    def __init__(self, params={}):
        self.params = params
        self.connection = self.create()

    def __repr__(self):
        return f'<{self.__class__.__name__}: active={self.is_active}>'

    @cached_property
    def get_connection(self):
        return self.connection

    @property
    def is_active(self):
        return self.connection_class is not None

    def create(self):
        """Creates a new connection"""
        if self.connection_class is None:
            raise ValueError('You need to specify a connection class')
        try:
            return self.connection_class(**self.params)
        except Exception as e:
            logger.error(f"Connection failed for {self.__class__.__name__}")
            return False

class RedisConnection(BaseConnection):
    """Base connection to a Redis database"""

    connection_class = redis.Redis

    def __init__(self, host='redis', port='6379', params={}):
        password = (
            os.getenv('REDIS_PASSWORD') or 
            get_key('.env', 'REDIS_PASSWORD')
        )
        base_params = {'host': host, 'port': port, 'password': password}
        redis_params = params | base_params
        super().__init__(params=redis_params)

    @property
    def is_active(self):
        result = super().is_active
        results_to_test = [result]
        try:
            self.get_connection.ping()
        except:
            results_to_test.append(False)
        return all(results_to_test)


class AirtableConnection(BaseConnection):
    """Base connection to an Airtable database"""

    connection_class = airtable.Airtable

    def __init__(self, base_id, api_key):
        airtable_params = {'base_id': base_id, 'api_key': api_key}
        super().__init__(params=airtable_params)


class NotionConnection(BaseConnection):
    pass


class GoogleSheetsConnection(BaseConnection):
    pass


class Memcache(BaseConnection):
    connection_class = pymemcache.Client

    def __init__(self, host='memcache', port=11211, **params):
        self.crendentials = (host, port)
        self.params = params
        self.connection = self.create()

    def create(self):
        if self.connection_class is None:
            raise ValueError('You need to specify a connection class')
        return self.connection_class(self.crendentials, **self.params)
