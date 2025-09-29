import pathlib

from regex import R


# Absolute path to the Kryptone project.
# This represents the root directory of the framework,
# useful for resolving paths to other resources within the project
GLOBAL_KRYPTONE_PATH = pathlib.Path(__file__).parent.parent.absolute()


# Absolute path to the local project
# This should be set to the root directory
# of your specific spider project
PROJECT_PATH = None


# Specifies the Selenium WebDriver to use for browser automation.
# Example values: 'Chrome', 'Firefox', 'Edge', etc.
WEBDRIVER = 'Chrome'


# Name of the media folder, used for storing
# resources like downloads and screenshots.
# The resolved path will point to
# `PROJECT_PATH / MEDIA_FOLDER`
MEDIA_FOLDER = 'media'


# Specifies the default wait time (in seconds)
# for the browser before navigating to the next URL
WAIT_TIME = 25


# Specifies a range for the browser's waiting time
# before moving to the next URL. Example: [10, 30] would
# randomly choose a wait time between 10 and 30 seconds
WAIT_TIME_RANGE = []


# Name of the file used for caching URLs
# to visit and already visited URLs
CACHE_FILE_NAME = 'cache'


# Frequency (in seconds) at which data
# is sent to registered webhooks
WEBHOOK_INTERVAL = 15

# Pagination size for data sent to webhooks.
# Data is only sent if the accumulated data size
# meets this threshold.
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
# Useful for text analysis and determining the stop
# words for content processing
WEBSITE_LANGUAGE = 'fr'


# Enable or disable headless mode for Selenium.
# When `True`, the browser will run in the
# background without displaying a UI.
HEADLESS = False


# Determines whether to load images
# when launching the browser
LOAD_IMAGES = True

# Determines whether to execute JavaScript
# when launching the browser
LOAD_JS = True


# IP address of the proxy server
# to use for web scraping. Example:
# '192.168.0.1:8080'
PROXY_IP_ADDRESS = None


# Storage settings for saving and retrieving data during spider execution

# A dictionary mapping storage aliases to their respective
# backend classes

# Example:

# 'default': 'kryptone.data_storages.FileStorage',
# 'backends': [{'name': 'redis', 'storage': ''kryptone.data_storages.RedisStorage''}]
STORAGES = {
    'default': 'kryptone.data_storages.FileStorage',
    'backends': []
}

# API endpoints for saving and retrieving data
# via external services
STORAGE_API_GET_ENDPOINT = None

STORAGE_API_SAVE_ENDPOINT = None

STORAGE_REDIS_HOST = 'localhost'

STORAGE_REDIS_PORT = 6379

STORAGE_REDIS_USERNAME = None

STORAGE_REDIS_PASSWORD = None

STORAGE_AIRTABLE_API_KEY = None

STORAGE_NOTION_TOKEN = None

STORAGE_NOTION_DATABASE_ID = None

STORAGE_GSHEET_SPREADSHEET_ID = None

STORAGE_GSHEET_CREDENTIALS = 'creds.json'

STORAGE_GSHEET_SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# Storage settings for memcache
# https://pymemcache.readthedocs.io/en/latest/getting_started.html

STORAGE_MEMCACHE_HOST = '127.0.0.1'

STORAGE_MEMCACHE_PORT = 11211

STORAGE_MEMCACHE_LOAD_BALANCER = []

# Storage settings for PG Admin

STORAGE_POSTGRESQL_DB_NAME = None

STORAGE_POSTGRESQL_USER = None

STORAGE_POSTGRESQL_PASSWORD = None

STORAGE_POSTGRESQL_HOST = None

STORAGE_POSTGRESQL_PORT = 5432

# Storage settings for Google Sheet

STORAGE_GOOGLE_SHEET_CREDENTIALS = None

STORAGE_GOOGLE_SHEET_ID = None


# RabbitMQ settings for task queueing

RABBITMQ_USER = 'guest'

RABBITMQ_PASSWORD = 'guest'

RABBITMQ_HOST = 'localhost'

RABBITMQ_PORT = 5672
