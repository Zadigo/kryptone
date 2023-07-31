import pathlib

# Absolute path to the local project
PROJECT_PATH = pathlib.Path(__file__).parent.absolute()


# Register spiders to crawl
# pages on a website
SPIDERS = ['Jennyfer']


# Register spiders to automate
# actions on a set of pages
AUTOMATERS = []


# Indicates the Selenium
# browser to use
WEBDRIVER = 'Edge'


# Indicates the name of the media folder
# which will also be used as a path
MEDIA_FOLDER = 'media'


# The amount of time the driver should
# wait before moving to the next url
WAIT_TIME = 5


# Indicates the range the driver should
# use as the waiting time before moving
# to the next url
WAIT_TIME_RANGE = [2, 5]


# The name of the file used to cache
# the urls to visit and the visited urls
CACHE_FILE_NAME = 'cache'


# Register additional storage backends to
# use for the project
ACTIVE_STORAGE_BACKENDS = []


# External storage backends to use to save the
# data gathered by the spiders
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
