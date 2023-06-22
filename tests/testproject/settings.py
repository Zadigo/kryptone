import pathlib

# Absolute path to the local project
PROJECT_PATH = pathlib.Path(__file__).resolve().parent


SPIDERS = [
    'Jennyfer'
]

AUTOMATERS = []


# The webdriver browser to use
WEBDRIVER = {
    'driver': 'selenium.webdriver.Edge',
    'executable_path': None,
}


MEDIA_FOLDER = 'media'


WAIT_TIME = 15


# External storage backends to use to save the
# data gathered by the spiders. The default storage
# method is a JSON file
STORAGE_BACKENDS = {
    'airtable': {
        'type': 'online',
        'credentials': {
            'API_KEY': None,
            'BASE_ID': None,
            'TABLE_NAME': None
        }
    },
    'google_sheets': {
        'type': 'online',
        'credentials': {
            'KEY': None,
            'item_name': None,
            'item_id': None
        }
    },
    'notion': {
        'type': 'online',
        'credentials': {
            'TOKEN': None,
            'DATABASE_ID': None
        }
    }
}


# Email setting values used essentially
# for alerting users for failed events
# or sending captured data
EMAIL_HOST = 'smtp.gmail'

EMAIL_HOST = None

EMAIL_PORT = 587

EMAIL_HOST_USER = None

EMAIL_HOST_PASSWORD = None

EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = None
