
import airtable
import requests

from kryptone.conf import settings
from kryptone.db.connections import redis_connection

AIRTABLE_ID_CACHE = set()


def airtable_backend(sender, **kwargs):
    """Use Airtable as a storage backend"""
    if 'airtable' in settings.ACTIVE_STORAGE_BACKENDS:
        config = settings.STORAGE_BACKENDS.get('airtable', None)
        if config is None:
            return False
        table = airtable.Airtable(
            config.get('base_id', None),
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
    if 'google sheets' in settings.ACTIVE_STORAGE_BACKENDS:
        pass


def redis_backend(sender, **kwargs):
    """Use Redis as a storage backend"""
    if 'redis' in settings.ACTIVE_STORAGE_BACKENDS:
        instance = redis_connection()
        if instance:
            pass
