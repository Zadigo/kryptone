import datetime
import pathlib


# Absolute path to the Kryptone project
GLOBAL_KRYPTONE_PATH = pathlib.Path(__file__).parent.parent.absolute()


# Absolute path to the local project
PROJECT_PATH = None


# Register spiders to crawl
# pages on a website
SPIDERS = []


# Indicates the Selenium
# browser to use
WEBDRIVER = 'Chrome'


# Indicates the name of the media folder
# which will also be used as a path
MEDIA_FOLDER = 'media'


# The amount of time the driver should
# wait before moving to the next url
WAIT_TIME = 25


# Indicates the range the driver should
# use as the waiting time before moving
# to the next url
WAIT_TIME_RANGE = []


# The name of the file used to cache
# the urls to visit and the visited urls
CACHE_FILE_NAME = 'cache'


# Register additional storage backends to
# use for the project
ACTIVE_STORAGE_BACKENDS = []


# External storage backends to configure
# for using in ACTIVE_STORAGE_BACKENDS
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
        'spreadsheet_id': None,
        'credentials': 'creds.json',
        'scopes': [
            'https://www.googleapis.com/auth/spreadsheets.readonly'
        ]
    },
    'notion': {
        'type': 'online',
        'credentials': {
            'TOKEN': None,
            'DATABASE_ID': None
        }
    },
    'webhooks': []
}

# Determines the frequency data should
# be sent in the webhooks registered in
# in storage backends
WEBHOOK_INTERVAL = 15

# Determines the amount of data that should
# be sent per request. If the amount of data
# is lowert than the pagination, the request
# is not sent until the requirement is met
WEBHOOK_PAGINATION = 100


# Email setting values used essentially
# for alerting users for failed events
# or sending captured data
EMAIL_HOST = 'smtp.gmail'

EMAIL_PORT = 587

EMAIL_HOST_USER = None

EMAIL_HOST_PASSWORD = None

EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = None


# The default language used by the website.
# This is useful when auditing the website by
# determining the nature of the stop words to
# block when gathering the text
WEBSITE_LANGUAGE = 'fr'
