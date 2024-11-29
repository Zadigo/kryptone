import os
import pathlib
import datetime
import unittest

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
        self.assertFalse(self.registry.is_ready)
        self.assertFalse(self.registry.has_running_spiders)

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

        from kryptone.conf import settings
        self.assertIsInstance(settings.MEDIA_FOLDER, pathlib.Path)

        self.assertIsInstance(settings.WEBHOOK_INTERVAL, datetime.timedelta)
