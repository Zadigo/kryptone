import pathlib


# Absolute path to the local project
PROJECT_PATH = None


# Register spiders to crawl
# the internet
SPIDERS = [
    'Jennyfer'
]


# Register spiders to automate
# actions on different websites
AUTOMATERS = []


# The browser to use
WEBDRIVER = 'selenium.webdriver.Chrome'


# The folder in which to save
# media files
MEDIA_FOLDER = 'media'


# The amount of time the driver should
# wait before moving to the next url
WAIT_TIME = 25


# The name of the cache file
# CACHE_FILE_NAME = 'cache.json'


# CACHE = {
#     'default': 'kryptone.cache.Cache',
#     'location': None
# }


# Additional storage backends to use
ACTIVE_STORAGE_BACKENDS = []


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
