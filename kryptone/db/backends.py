
import sqlite3
from venv import logger

import airtable
import gspread
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from kryptone import logger
from kryptone.conf import settings
from kryptone.db import BaseConnection
from kryptone.db.connections import redis_connection
from kryptone.utils.file_readers import write_json_document

AIRTABLE_ID_CACHE = set()


def airtable_backend(sender, **kwargs):
    """Use Airtable as a storage backend"""
    if 'airtable' in settings.ACTIVE_STORAGE_BACKENDS:
        config = settings.STORAGE_BACKENDS.get('airtable', None)
        if config is None:
            return False
        table = airtable.Airtable(
            config.get('base_id', None),
            config.get('table_name', None),
            config.get('api_key', None)
        )
        records = []
        for item in sender.final_result:
            record = {}
            for key, value in item.items():
                if key == 'id':
                    AIRTABLE_ID_CACHE.add(value)

                if key == 'id' and value in AIRTABLE_ID_CACHE:
                    continue

                record[key.title()] = value
            records.append(record)
        AIRTABLE_ID_CACHE.clear()
        return table.batch_insert(records)


def notion_backend(sender, **kwargs):
    """Use Notion as a storage backend"""
    if 'notion' in settings.ACTIVE_STORAGE_BACKENDS:
        config = settings.STORAGE_BACKENDS.get('notion', None)
        if config is None:
            return False
        headers = {
            'Authorization': f'Bearer {config["token"]}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-02-22'
        }
        try:
            url = f'https://api.notion.com/v1/databases/{config["database_id"]}'
            response = requests.post(url, headers=headers)
        except:
            return False
        else:
            if response.ok:
                return response.json()
            return False


def google_sheets_backend(sender, **kwargs):
    """Use Google Sheets as a storage backend"""
    # if 'google sheets' in settings.ACTIVE_STORAGE_BACKENDS:
    google_sheet_settings = settings.STORAGE_BACKENDS['google_sheets']
    project_path = settings.PROJECT_PATH

    if project_path is None:
        logger.critical("Cannot find 'creds.json' for Google sheet API")
    else:
        file_path = project_path / google_sheet_settings['credentials']
        worksheet = gspread.service_account(filename=file_path)

        # connect to your sheet (between "" = the name of your G Sheet, keep it short)
        sheet = worksheet.open(google_sheet_settings['sheet_name']).sheet1

        # get the values from cells a2 and b2
        name = sheet.acell("a2").value
        website = sheet.acell("b2").value
        print(name, website)

        # write values in cells a3 and b3
        sheet.update('a3', 'Chat GPT')
        sheet.update("b3", "openai.com")


def redis_backend(sender, **kwargs):
    """Use Redis as a storage backend"""
    if 'redis' in settings.ACTIVE_STORAGE_BACKENDS:
        instance = redis_connection()
        if instance:
            instance.hset('cache', None)


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
            logger.critical(
                f"{self.__class__.__name__} connection "
                "should be a ran in a project"
            )
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


class SQL:
    SELECT = 'select {fields} from {table} where {params}'
    WHERE_CLAUSE = 'where {params}'
    CREATE_TABLE = 'create table if not exists {table} ({params})'

    def finalize_sql(self, sql):
        if sql.endswith(';'):
            return sql
        return f'{sql};'


class SQliteBackend(SQL):
    def __init__(self, database=None):
        self.database = database or ':memory:'
        self.connection = sqlite3.connect(self.database)

    def __getitem__(self, key):
        sql = self.finalize_sql(
            self.SELECT.format(fields=key, table=self.name, params='key=?')
        )
        print(sql)
        result = self.connection.execute(sql)
        if not result:
            raise KeyError()
        return result

    def __setitem__(self, key):
        pass

    def __delitem__(self, key):
        pass

    def __len__(self):
        pass

    def __iter__(self):
        pass

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self):
        pass

    def __del__(self):
        pass

    def keys(self):
        pass

    def values(self):
        pass

    def items(self):
        pass

    def update(self, column, value):
        pass

    def bulk_update(self, columns, values):
        pass

    def filter(self, *args, **kwargs):
        pass

    def create(self, **kwargs):
        pass


class Table(SQliteBackend):
    def __init__(self, name, *, fields=[]):
        super().__init__()
        self.fields = fields
        self.name = name
        self.connection.execute(self.create_table_sql())
        self.connection.commit()

    def create_table_sql(self):
        sql = self.CREATE_TABLE.format(
            table=self.name, params='key integer primary key, value blob')
        return self.finalize_sql(sql)


# c = Table('seen_urls', fields=[('url', ('integer', 'primary key')), ])
# print(c['url'])
