from unittest import TestCase

from kryptone import logger
from kryptone.utils.text import LogStyle, color_text


class TestLogging(TestCase):
    def test_structure(self):
        logger.info('Info')
        logger.warning('Warning')
        logger.error('Error')
        logger.debug('Debug')
        logger.critical('Critical')

    def test_coloring(self):
        instance = LogStyle('My text')
        logger.info(instance.red_text())
        logger.info(instance.yellow_text())
        logger.info(instance.green_text())
        logger.info(instance.gray_text())
        logger.info(instance.blue_text())
        logger.info(instance.CROSS_MARK + instance.red_text())

        instance = LogStyle('My text', background=True)
        logger.info(instance.blue_text())
    
    def test_color_text_method(self):
        logger.info(color_text('red', 'My text'))
