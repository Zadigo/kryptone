
import airtable
import requests
import gspread
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
    if 'google sheets' in settings.ACTIVE_STORAGE_BACKENDS:
        google_sheet_settings = settings.STORAGE_BACKENDS['google_sheets']
        worksheet = gspread.service_account(filename=google_sheet_settings['credentials'])

        #connect to your sheet (between "" = the name of your G Sheet, keep it short)
        sheet = worksheet.open(google_sheet_settings['sheet_name']).sheet1

        #get the values from cells a2 and b2
        name = sheet.acell("a2").value
        website = sheet.acell("b2").value
        print(name, website)

        #write values in cells a3 and b3
        sheet.update("a3", "Chat GPT")
        sheet.update("b3", "openai.com")


def redis_backend(sender, **kwargs):
    """Use Redis as a storage backend"""
    if 'redis' in settings.ACTIVE_STORAGE_BACKENDS:
        instance = redis_connection()
        if instance:
            instance.hset('cache', None)
