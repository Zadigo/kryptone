import pathlib

# Absolute path to the local project
PROJECT_PATH = pathlib.Path(__file__).resolve().parent


SPIDERS = [
    'Jennyfer'
]


# The webdriver browser to use
WEBDRIVER = {
    'driver': 'selenium.webdriver.Edge',
    'executable_path': None,
}


MEDIA_FOLDER = 'media'
