import datetime
import os
import pathlib
import unittest
from importlib import import_module
from unittest import mock
from unittest.mock import MagicMock, patch

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


class TestSpiderConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spider_name = 'ExampleSpider'
        module = import_module('tests.testproject.spiders')

        cls.config = SpiderConfig(spider_name, module)

    def test_structure(self):
        self.assertIsNotNone(self.config.spider_class)
        self.assertIsNotNone(self.config.path)

        mocked_spider = MagicMock()
        mocked_spider.boost_start.return_value = mock.Mock()
        mocked_spider.start.return_value = mock.Mock()

        with patch.object(SpiderConfig, 'get_spider_instance') as mock_method:
            mock_method.return_value = mocked_spider

            self.config.run(windows=10)
            mocked_spider.boost_start.assert_called()

            self.config.run()
            mocked_spider.start.assert_called()
