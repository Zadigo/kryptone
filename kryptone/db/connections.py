import functools
from venv import logger

import redis
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from kryptone import logger
from kryptone.conf import settings
from kryptone.db import BaseConnection
from kryptone.utils.file_readers import write_json_document


@functools.lru_cache(maxsize=1)
def redis_connection(host='redis', port=6379):
    instance = redis.Redis(host, port)
    logger.info('Connecting to Redis client...')
    try:
        instance.ping()
    except:
        logger.warning('Redis connection failed')
        return False
    else:
        return instance


@functools.lru_cache(maxsize=1)
def memcache_connection(host='memcache', port=11211):
    from pymemcache.client.base import Client
    instance = Client(f'{host}:{port}')
    logger.info('Connecting to PyMemcache client...')
    try:
        instance._connect()
    except:
        logger.warning('PyMemcache connection failed')
        return False
    else:
        return instance


class GoogleSheets(BaseConnection):
    def __init__(self):
        self.credentials = None
        self.service = None

        storage_backends = settings.STORAGE_BACKENDS
        self.connection_settings = storage_backends.get(
            'google_sheets', None
        )

        if self.connection_settings is None:
            raise ValueError()

        project_path = settings.PROJECT_PATH
        if project_path is None:
            logger.critical(f"{self.__class__.__name__} connection "
                            "should be a ran in a project")
        else:
            try:
                tokens_file_path = project_path / \
                    self.connection_settings['credentials']
            except KeyError:
                raise
            else:
                if tokens_file_path.exists():
                    self.credentials = Credentials.from_authorized_user_file(
                        tokens_file_path,
                        self.connection_settings['scopes']
                    )

                if not self.credentials is None or not self.credentials.valid:
                    if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                        self.credentials.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            tokens_file_path,
                            self.connection_settings['scopes']
                        )
                        self.credentials = flow.run_local_server(port=0)

                    # Save the credentials for the next run
                    write_json_document(
                        self.connection_settings['credentials'],
                        self.credentials.to_json()
                    )

    def connect(self):
        try:
            self.service = build('sheets', 'v4', credentials=self.credentials)
        except HttpError as e:
            logger.error(e.args)
