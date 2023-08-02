import logging
from kryptone.signals import Signal


class Logger:
    instance = None

    def __init__(self, name='KRYPTONE'):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        logger.addHandler(handler)

        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M'
        )
        handler.setFormatter(log_format)

        file_handler = logging.FileHandler('access.log')
        logger.addHandler(file_handler)
        file_handler.setFormatter(log_format)

        self.instance = logger

    @classmethod
    def create(cls, name):
        instance = cls(name=name)
        return instance
    
    def warning(self, message, *args, **kwargs):
        self.instance.warning(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self.instance.info(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.instance.error(message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self.instance.debug(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        self.instance.critical(message, *args, **kwargs)


logger = Logger()


def setup():
    """Initial entrypoint that allows the configuration
    of a Krytone project by populating the application
    with the spiders"""
    from kryptone.registry import registry
    registry.populate()
