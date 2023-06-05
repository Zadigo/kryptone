import pathlib

# Absolute path to the Kryptone project
# os.path.dirname(os.path.dirname(__file__))
# GLOBAL_KRYPTONE_PATH = pathlib.Path('.').parent.absolute()
GLOBAL_KRYPTONE_PATH = pathlib.Path(__file__).parent.parent.absolute()


# Absolute path to the local project
PROJECT_PATH = None


# The webdriver browser to use
WEBDRIVER = {
    'driver': 'selenium.webdriver.Edge',
    'executable_path': 'WEBDRIVER_EXECUTABLE_PATH',
}


# The name of the cache file
CACHE_FILE_NAME = 'cache.json'


CACHE = {
    'default': 'kryptone.cache.Cache',
    'location': None
}
