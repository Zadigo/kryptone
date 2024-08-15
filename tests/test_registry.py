import os
import pathlib
import unittest

from kryptone.registry import (ENVIRONMENT_VARIABLE, MasterRegistry,
                               SpiderConfig)


class TestMasterRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = MasterRegistry()

    def test_structure(self):
        self.assertFalse(self.registry.is_ready)
        self.assertFalse(self.registry.has_running_spiders)

    def test_populate(self):
        from kryptone.conf import settings
        path = pathlib.Path('./tests/testproject').absolute()
        setattr(settings, 'PROJECT_PATH', path)
        os.environ.setdefault(ENVIRONMENT_VARIABLE, 'tests.testproject')
        self.registry.populate()

        self.assertTrue(self.registry.has_spiders)
        self.assertTrue(self.registry.has_spider('Jennyfer'))
        self.assertIsInstance(
            self.registry.get_spider('Jennyfer'),
            SpiderConfig
        )


if __name__ == '__main__':
    unittest.main()
