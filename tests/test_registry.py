import datetime
import os
import pathlib
import unittest
from importlib import import_module
from unittest.mock import patch

from kryptone.registry import (ENVIRONMENT_VARIABLE, MasterRegistry,
                               SpiderConfig)


class TestMasterRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kryptone.conf import settings

        # The registry is auto called
        # in registry.py
        cls.registry = MasterRegistry()
        cls.project = path = pathlib.Path('./tests/testproject').absolute()
        setattr(settings, 'PROJECT_PATH', path)

    def setUp(self):
        os.environ.setdefault(ENVIRONMENT_VARIABLE, 'tests.testproject')

    def test_structure(self):
        instance = MasterRegistry()
        self.assertFalse(instance.is_ready)
        self.assertFalse(instance.has_running_spiders)

    def test_populate(self):
        self.registry.populate()

        self.assertTrue(self.registry.has_spiders)
        self.assertTrue(self.registry.has_spider('ExampleSpider'))

        self.assertIsInstance(
            self.registry.get_spider('ExampleSpider'),
            SpiderConfig
        )

        self.assertEqual(self.registry.project_name, 'testproject')
        self.assertIsNotNone(self.registry.absolute_path)
        self.assertTrue(self.registry.absolute_path.exists())

        from kryptone.conf import settings

        self.assertIsInstance(settings.MEDIA_FOLDER, pathlib.Path)
        self.assertIsInstance(settings.WEBHOOK_INTERVAL, datetime.timedelta)

        spider = self.registry.get_spider('ExampleSpider')
        self.assertIsNotNone(spider)
        self.assertIsInstance(spider, SpiderConfig)


@patch('tests.testproject.spiders')
class TestSpiderConfig(unittest.TestCase):
    def test_structure(self, mocked_module):
        print(mocked_module)
        spider_name = 'ExampleSpider'
        module = import_module('tests.testproject')

        config = SpiderConfig(spider_name, module)
        self.assertIsNotNone(config.spider_class)
        config.run()
