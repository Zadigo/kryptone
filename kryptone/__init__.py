import logging
import pathlib

from kryptone.cache import Cache
from kryptone.conf.settings import Settings

settings = Settings()

PROJECT_PATH = pathlib.Path('.').absolute()


class Logger:
    instance = None

    def __init__(self, name='KRYPTONE'):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        logger.addHandler(handler)

        # file_handler = logging.FileHandler('access.log')
        # logger.addHandler(file_handler)

        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d'
        )
        handler.setFormatter(log_format)
        # file_handler.setFormatter(log_format)
        self.instance = logger

    @classmethod
    def create(cls, name):
        instance = cls(name=name)
        return instance

    def info(self, message, *args, **kwargs):
        self.instance.info(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.instance.error(message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self.instance.debug(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        self.instance.critical(message, *args, **kwargs)


logger = Logger()

cache = Cache()