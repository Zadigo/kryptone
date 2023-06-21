import pathlib

# Absolute path to the Kryptone project
GLOBAL_KRYPTONE_PATH = pathlib.Path(__file__).parent.parent.absolute()


# Absolute path to the local project
PROJECT_PATH = None


# Register spiders to crawl
# the internet
SPIDERS = []


# Register spiders to automate
# actions on different websites
AUTOMATERS = []


# The browser to use
WEBDRIVER = {
    'driver': 'selenium.webdriver.Edge',
    'executable_path': None,
}


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
