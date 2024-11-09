import pathlib


# Absolute path to the Kryptone project
GLOBAL_KRYPTONE_PATH = pathlib.Path(__file__).parent.parent.absolute()


# Absolute path to the local project
PROJECT_PATH = None


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


# Allow Selenium to be launched in headless mode
HEADLESS = False


# Load all images when launching the browser
LOAD_IMAGES = True

# Load JS codes when launching the browser
LOAD_JS = True


# Use a proxy addresses
PROXY_IP_ADDRESS = None


# A list of storage paths to
# use when storing or retrieving
# data for the Spiders
STORAGES = {
    'default': 'kryptone.storages.FileStorage',
    'backends': []
}

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
