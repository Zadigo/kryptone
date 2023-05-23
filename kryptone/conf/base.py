import pathlib

PROJECT_PATH = pathlib.Path('.').parent.absolute()


WEBDRIVER = {
    'driver': 'selenium.webdriver.Edge',
    'executable_path': 'WEBDRIVER_EXECUTABLE_PATH',
}


CACHE_FILE_NAME = 'cache.json'


CACHE = {
    'default': 'kryptone.cache.Cache',
    'location': PROJECT_PATH / CACHE_FILE_NAME,
}
